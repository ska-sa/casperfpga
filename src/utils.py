__author__ = 'paulp'

import threading
import Queue
import time
import logging
from katcp_client_fpga import KatcpClientFpga
import qdr

LOGGER = logging.getLogger(__name__)


def calibrate_qdrs(fpga_list, timeout):
    """
    Software calibrate all the QDRs on a list of FPGAs.
    Threaded to save time.
    :param fpga_list: a List of CASPER FPGAs
    :param timeout: how long to wait
    :return: a dictionary containing the calibration status of all the FPGAs in the list.
    """
    return threaded_fpga_operation(fpga_list, qdr.calibrate_qdrs, -1, timeout)


def program_fpgas(fpga_list, progfile, timeout=10):
    """
    Program more than one FPGA at the same time.
    :param fpga_list: a list of objects for the FPGAs to be programmed
    :param progfile: string, the filename of the file to use to program the FPGAs
    :return: <nothing>
    """
    stime = time.time()
    chilltime = 0.1
    waiting = []
    for fpga in fpga_list:
        try:
            len(fpga)
        except TypeError:
            fpga.upload_to_ram_and_program(progfile, wait_complete=False)
            waiting.append(fpga)
        else:
            fpga[0].upload_to_ram_and_program(fpga[1], wait_complete=False)
            waiting.append(fpga[0])
    starttime = time.time()
    while time.time() - starttime < timeout:
        donelist = []
        for fpga in waiting:
            if fpga.is_running():
                donelist.append(fpga)
        for done in donelist:
            waiting.pop(waiting.index(done))
        if len(waiting) > 0:
            time.sleep(chilltime)
        else:
            break
    if len(waiting) > 0:
        raise RuntimeError('Timed out waiting for FPGA programming to complete.')
    LOGGER.info('Programming %d FPGAs took %.3f seconds.' % (len(fpga_list), time.time() - stime))


def threaded_create_fpgas_from_hosts(host_list, port=7147, timeout=10):
    """
    Create KatcpClientFpga objects in many threads, Moar FASTAAA!
    :param host_list:
    :return:
    """
    def makefpga(resultq, host):
        resultq.put_nowait(KatcpClientFpga(host, port))

    results = Queue.Queue(maxsize=len(host_list))
    thread_list = []
    for host_ in host_list:
        thread = threading.Thread(target=makefpga, args=(results, host_))
        thread.daemon = True
        thread.start()
        thread_list.append(thread)
    for thread_ in thread_list:
        thread_.join(timeout)
    fpgas = []
    while not results.empty():
        result = results.get()
        fpgas.append(result)
    return fpgas


def threaded_fpga_function(fpga_list, timeout, function_name, *function_args):
    """
    Thread the running of any KatcpClientFpga function on a list of KatcpClientFpga objects.
    Much faster.
    :param fpgas: list of KatcpClientFpga objects
    :param timeout: how long to wait before timing out
    :param function_name: the KatcpClientFpga function to run e.g. 'disconnect' for fpgaobj.disconnect()
    :param function_args: a dictionary, keyed by hostname, of the results from the function
    :return:
    """
    def dofunc(resultq, fpga):
        rv = eval('fpga.%s' % function_name)(*function_args)
        resultq.put_nowait((fpga.host, rv))
    results = Queue.Queue(maxsize=len(fpga_list))
    thread_list = []
    for fpga_ in fpga_list:
        thread = threading.Thread(target=dofunc, args=(results, fpga_))
        thread.daemon = True
        thread.start()
        thread_list.append(thread)
    for thread_ in thread_list:
        thread_.join(timeout)
    returnval = {}
    while not results.empty():
        result = results.get()
        returnval[result[0]] = result[1]
    return returnval


def threaded_fpga_operation(fpga_list, job_function, num_threads=-1, *job_args):
    """
    Run any function on a list of KatcpClientFpga objects in a specified number of threads.
    :param fpga_list: list of KatcpClientFpga objects
    :param job_function: the function to be run - MUST take the FpgaClient object as its first argument
    :param num_threads: how many threads should be used. Default is one per list item
    :param job_args: further arugments for the job_function
    :return: a dictionary, keyed by hostname, of the results from the function
    """
    """
    Example:
    def xread_all_new(self, register, bram_size, offset = 0):
         import threaded
         def xread_all_thread(host):
             return host.read(register, bram_size, offset)
         vals = threaded.fpga_operation(self.xfpgas, num_threads = -1, job_function = xread_all_thread)
         rv = []
         for x in self.xfpgas: rv.append(vals[x.host])
         return rv
    """

    if job_function is None:
        raise RuntimeError("No job_function? Not allowed!")

    class CorrWorker(threading.Thread):
        def __init__(self, request_q, result_q, job_func, *jfunc_args):
            """
            A thread that does a job on an FPGA - i.e. calls a function on an FPGA.
            :param request_q:
            :param result_q:
            :param job_func:
            :param jfunc_args:
            :return:
            """
            self.request_queue = request_q
            self.result_queue = result_q
            self.job = job_func
            self.job_args = jfunc_args
            threading.Thread.__init__(self)

        def run(self):
            done = False
            while not done:
                try:
                    # get a job from the queue - in this case, get a fpga host from the queue
                    request_host = self.request_queue.get(block=False)
                    # do some work - run the job function on the host
                    try:
                        res = self.job(request_host, *self.job_args)
                    except Exception as exc:
                        errstr = "Job %s internal error: %s, %s" % (self.job.func_name, type(exc), exc)
                        res = RuntimeError(errstr)
                    # put the result on the result queue
                    self.result_queue.put((request_host.host, res))
                    # and notify done
                    self.request_queue.task_done()
                except Queue.Empty:
                    done = True

    if num_threads == -1:
        num_threads = len(fpga_list)
    request_queue = Queue.Queue()
    result_queue = Queue.Queue()
    # put the fpgas into a Thread-safe Queue
    for fpga_ in fpga_list:
        if not isinstance(fpga_, KatcpClientFpga):
            raise TypeError('Currently this function only supports KatcpClientFpga objects.')
        request_queue.put(fpga_)
    # make as many worker threads a specified and start them off
    workers = [CorrWorker(request_queue, result_queue, job_function, *job_args) for _ in range(0, num_threads)]
    for w in workers:
        w.daemon = True
        w.start()
    # join the last one to wait for completion
    request_queue.join()
    # format the result into a dictionary by host
    rv = {}
    while not result_queue.empty():
        result = result_queue.get()
        rv[result[0]] = result[1]
    return rv


def threaded_non_blocking_request(fpga_list, timeout, request, request_args):
    """
    Make a non-blocking KatCP request to a list of KatcpClientFpgas, using the Asynchronous client.
    :param fpga_list: list of KatcpClientFpga objects
    :param timeout: the request timeout
    :param request: the request string
    :param request_args: the arguments to the request, as a list
    :return: a dictionary, keyed by hostname, of result dictionaries containing reply and informs
    """
    reply_queue = Queue.Queue(maxsize=len(fpga_list))
    requests = {}
    replies = {}

    # reply callback
    def reply_cb(host, req_id):
        LOGGER.debug('Reply(%s) from host(%s)' % (req_id, host))
        reply_queue.put_nowait([host, req_id])

    # start the requests
    LOGGER.debug('Send request(%s) to %i hosts.' % (request, len(fpga_list)))
    lock = threading.Lock()
    for fpga_ in fpga_list:
        lock.acquire()
        req = fpga_.nb_request(request, None, reply_cb, *request_args)
        requests[req['host']] = [req['request'], req['id']]
        lock.release()
        LOGGER.debug('Request \'%s\' id(%s) to host(%s)' % (req['request'], req['id'], req['host']))

    # wait for replies from the requests
    timedout = False
    done = False
    while (not timedout) and (not done):
        try:
            it = reply_queue.get(block=True, timeout=timeout)
        except:
            timedout = True
            break
        replies[it[0]] = it[1]
        if len(replies) == len(fpga_list):
            done = True
    if timedout:
        LOGGER.error('non_blocking_request timeout after %is.' % timeout)
        LOGGER.error(replies)
        raise RuntimeError('non_blocking_request timeout after %is.' % timeout)

    # process the replies
    rv = {}
    for fpga_ in fpga_list:
        try:
            request_id = replies[fpga_.host]
        except KeyError:
            LOGGER.error(replies)
            raise KeyError('Didn\'t get a reply for FPGA \'%s\' so the '
                           'request \'%s\' probably didn\'t complete.' % (fpga_.host, request))
        reply, informs = fpga_.nb_get_request_result(request_id)
        frv = {'request': requests[fpga_.host][0],
               'reply': reply.arguments[0],
               'reply_args': reply.arguments}
        informlist = []
        for inf in informs:
            informlist.append(inf.arguments)
        frv['informs'] = informlist
        rv[fpga_.host] = frv
        fpga_.nb_pop_request_by_id(request_id)
    return rv

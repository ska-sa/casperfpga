__author__ = 'paulp'

import threading
import Queue
import time
import logging

LOGGER = logging.getLogger(__name__)


def create_meta_dictionary(metalist):
    """
    Build a meta information dictionary from a provided raw meta info list.
    :param metalist: a list of all meta information about the system
    :return: a dictionary of device info, keyed by unique device name
    """
    meta_items = {}
    for name, tag, param, value in metalist:
        if name not in meta_items.keys():
            meta_items[name] = {}
        try:
            if meta_items[name]['tag'] != tag:
                raise ValueError('Different tags - %s, %s - for the same item %s' %
                                 (meta_items[name]['tag'], tag, name))
        except KeyError:
            meta_items[name]['tag'] = tag
        meta_items[name][param] = value
    return meta_items


def parse_fpg(filename):
    """
    Read the meta information from the FPG file.
    :param filename: the name of the fpg file to parse
    :return: device info dictionary, memory map info (coreinfo.tab) dictionary
    """
    LOGGER.debug('Parsing file %s for system information' % filename)
    if filename is not None:
        fptr = open(filename, 'r')
        firstline = fptr.readline().strip().rstrip('\n')
        if firstline != '#!/bin/kcpfpg':
            fptr.close()
            raise RuntimeError('%s does not look like an fpg file we can parse.' % filename)
    else:
        raise IOError('No such file %s' % filename)
    memorydict = {}
    metalist = []
    done = False
    while not done:
        line = fptr.readline().strip().rstrip('\n')
        if line.lstrip().rstrip() == '?quit':
            done = True
        elif line.startswith('?meta'):
            line = line.replace('\_', ' ').replace('?meta ', '').replace('\n', '').lstrip().rstrip()
            name, tag, param, value = line.split('\t')
            name = name.replace('/', '_')
            metalist.append((name, tag, param, value))
        elif line.startswith('?register'):
            register = line.replace('\_', ' ').replace('?register ', '').replace('\n', '').lstrip().rstrip()
            name, address, size_bytes = register.split(' ')
            address = int(address, 16)
            size_bytes = int(size_bytes, 16)
            if name in memorydict.keys():
                raise RuntimeError('%s: mem device %s already in dictionary' % (filename, name))
            memorydict[name] = {'address': address, 'bytes': size_bytes}
    fptr.close()
    return create_meta_dictionary(metalist), memorydict


def program_fpgas(fpga_list, progfile, timeout=10):
    """
    Program more than one FPGA at the same time.
    :param fpga_list: a list of objects for the FPGAs to be programmed
    :param progfile: string, the filename of the file to use to program the FPGAs
    :return: <nothing>
    """
    stime = time.time()
    new_dict = {}
    new_list = []
    for fpga in fpga_list:
        try:
            len(fpga)
        except TypeError:
            _tuple = (fpga, progfile)
        else:
            _tuple = (fpga[0], fpga[1])
        new_dict[_tuple[0].host] = _tuple[1]
        new_list.append(_tuple[0])

    def _prog_fpga(_fpga):
        _fpga.upload_to_ram_and_program(new_dict[_fpga.host])
    threaded_fpga_operation(fpga_list=new_list, timeout=timeout, target_function=(_prog_fpga,))
    LOGGER.info('Programming %d FPGAs took %.3f seconds.' % (len(fpga_list), time.time() - stime))


def threaded_create_fpgas_from_hosts(fpga_class, host_list, port=7147, timeout=10):
    """
    Create KatcpClientFpga objects in many threads, Moar FASTAAA!
    :param fpga_class: the class to instantiate - KatcpFpga or DcpFpga
    :param host_list: a comma-seperated list of hosts
    :param port: the port on which to do network comms
    :param timeout: how long to wait, in seconds
    :return:
    """
    num_hosts = len(host_list)
    result_queue = Queue.Queue(maxsize=num_hosts)
    thread_list = []
    for host_ in host_list:
        thread = threading.Thread(target=lambda hostname: result_queue.put_nowait(fpga_class(hostname, port)),
                                  args=(host_,))
        thread.daemon = True
        thread.start()
        thread_list.append(thread)
    for thread_ in thread_list:
        thread_.join(timeout)
    fpgas = []
    while True:
        try:
            result = result_queue.get_nowait()
            fpgas.append(result)
        except Queue.Empty:
            break
    if len(fpgas) != num_hosts:
        print fpgas
        raise RuntimeError('Given %d hosts, only made %d %ss' % (num_hosts, len(fpgas), fpga_class))
    return fpgas


def _check_target_func(target_function):
    if isinstance(target_function, basestring):
        return target_function, (), {}
    try:
        len(target_function)
    except TypeError:
        return target_function, (), {}
    if len(target_function) == 3:
        return target_function
    elif len(target_function) == 1:
        target_function = (target_function[0], (), {})
    elif len(target_function) == 2:
        target_function = (target_function[0], target_function[1], {})
    else:
        raise RuntimeError('target_function tuple too long? - (name, (), {})')
    return target_function


def threaded_fpga_function(fpga_list, timeout, target_function):
    """
    Thread the running of any KatcpClientFpga function on a list of KatcpClientFpga objects.
    Much faster.
    :param fpgas: list of KatcpClientFpga objects
    :param timeout: how long to wait before timing out
    :param target_function: a tuple with three parts:
                            1. string, the KatcpClientFpga function to
                               run e.g. 'disconnect' for fpgaobj.disconnect()
                            2. tuple, the arguments to the function
                            3. dict, the keyword arguments to the function
                            e.g. (func_name, (1,2,), {'another_arg': 3})
    :return: a dictionary of the results, keyed on hostname
    """
    target_function = _check_target_func(target_function)

    def dofunc(fpga, *args, **kwargs):
        rv = eval('fpga.%s' % target_function[0])(*args, **kwargs)
        return rv
    return threaded_fpga_operation(fpga_list, timeout, (dofunc, target_function[1], target_function[2]))


def threaded_fpga_operation(fpga_list, timeout, target_function):
    """
    Thread any operation against many FPGA objects
    :param fpgas: list of KatcpClientFpga objects
    :param timeout: how long to wait before timing out
    :param target_function: a tuple with three parts:
                            1. reference, the function object that must be
                               run - MUST take FPGA object as first argument
                            2. tuple, the arguments to the function
                            3. dict, the keyword arguments to the function
                            e.g. (func_name, (1,2,), {'another_arg': 3})
    :return: a dictionary of the results, keyed on hostname
    """
    target_function = _check_target_func(target_function)

    def jobfunc(resultq, fpga):
        rv = target_function[0](fpga, *target_function[1], **target_function[2])
        resultq.put_nowait((fpga.host, rv))
    num_fpgas = len(fpga_list)
    result_queue = Queue.Queue(maxsize=num_fpgas)
    thread_list = []
    for fpga_ in fpga_list:
        thread = threading.Thread(target=jobfunc, args=(result_queue, fpga_))
        thread.daemon = True
        thread.start()
        thread_list.append(thread)
    for thread_ in thread_list:
        thread_.join(timeout)
        if thread_.isAlive():
            break
    returnval = {}
    while True:
        try:
            result = result_queue.get_nowait()
            returnval[result[0]] = result[1]
        except Queue.Empty:
            break
    if len(returnval) != num_fpgas:
        print returnval
        raise RuntimeError('Given %d FPGAs, only got %d results, must '
                           'have timed out.' % (num_fpgas, len(returnval)))
    return returnval


def threaded_non_blocking_request(fpga_list, timeout, request, request_args):
    """
    Make a non-blocking KatCP request to a list of KatcpClientFpgas, using the Asynchronous client.
    :param fpga_list: list of KatcpClientFpga objects
    :param timeout: the request timeout
    :param request: the request string
    :param request_args: the arguments to the request, as a list
    :return: a dictionary, keyed by hostname, of result dictionaries containing reply and informs
    """
    num_fpgas = len(fpga_list)
    reply_queue = Queue.Queue(maxsize=num_fpgas)
    requests = {}
    replies = {}

    # reply callback
    def reply_cb(host, req_id):
        LOGGER.debug('Reply(%s) from host(%s)' % (req_id, host))
        reply_queue.put_nowait([host, req_id])

    # start the requests
    LOGGER.debug('Send request(%s) to %i hosts.' % (request, num_fpgas))
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
        if len(replies) == num_fpgas:
            done = True
    if timedout:
        LOGGER.error('non_blocking_request timeout after %is.' % timeout)
        LOGGER.error(replies)
        raise RuntimeError('non_blocking_request timeout after %is.' % timeout)

    # process the replies
    returnval = {}
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
        returnval[fpga_.host] = frv
        fpga_.nb_pop_request_by_id(request_id)
    return returnval


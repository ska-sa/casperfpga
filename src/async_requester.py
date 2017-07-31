import logging
import threading
import time
from katcp import Message

LOGGER = logging.getLogger(__name__)

raise DeprecationWarning


class AsyncRequester(object):
    """
    A class to hold information about a specific KATCP request made by a FPGA.
    """
    def __init__(self, host, request_func, max_requests=100):
        self.host = host
        self._nb_request_id_lock = threading.Lock()
        self._nb_request_id = 0
        self._nb_requests_lock = threading.Lock()
        self._nb_requests = {}
        self._nb_max_requests = max_requests
        self._nb_request_func = request_func

    def nb_get_request_by_id(self, request_id):
        """

        :param request_id:
        :return:
        """
        try:
            return self._nb_requests[request_id]
        except KeyError:
            return None

    def nb_pop_request_by_id(self, request_id):
        """

        :param request_id:
        :return:
        """
        try:
            self._nb_requests_lock.acquire()
            r = self._nb_requests.pop(request_id)
            self._nb_requests_lock.release()
            return r
        except KeyError:
            return None

    def nb_pop_oldest_request(self):
        """

        :return:
        """
        req = self._nb_requests[self._nb_requests.keys()[0]]
        for v in self._nb_requests.itervalues():
            if v.time_tx < req.time_tx:
                req = v
        self._nb_requests_lock.acquire()
        r = self.nb_pop_request_by_id(req.request_id)
        self._nb_requests_lock.release()
        return r

    def nb_get_request_result(self, request_id):
        """

        :param request_id:
        :return:
        """
        req = self.nb_get_request_by_id(request_id)
        return req.reply, req.informs

    def nb_add_request(self, request_name, request_id, inform_cb, reply_cb):
        """

        :param request_name:
        :param request_id:
        :param inform_cb:
        :param reply_cb:
        :return:
        """
        if request_id in self._nb_requests.keys():
            raise RuntimeError('Trying to add request with id(%s) but it '
                               'already exists.' % request_id)
        self._nb_requests_lock.acquire()
        self._nb_requests[request_id] = AsyncRequest(
            self.host, request_name, request_id, inform_cb, reply_cb)
        self._nb_requests_lock.release()

    def nb_get_next_request_id(self):
        """

        :return:
        """
        self._nb_request_id_lock.acquire()
        self._nb_request_id += 1
        reqid = self._nb_request_id
        self._nb_request_id_lock.release()
        return str(reqid)

    def nb_replycb(self, msg, *userdata):
        """
        The callback for request replies. Check that the ID exists and
        call that request's got_reply function.
        :param msg - the received message
        :param userdata
        """
        request_id = ''.join(userdata)
        if request_id not in self._nb_requests.keys():
            raise RuntimeError('Recieved reply for request_id(%s), but no such '
                               'stored request.' % request_id)
        self._nb_requests[request_id].got_reply(msg.copy())

    def nb_informcb(self, msg, *userdata):
        """
        The callback for request informs. Check that the ID exists and
        call that request's got_inform function.
        :param msg - the received message
        :param userdata
        """
        request_id = ''.join(userdata)
        if request_id not in self._nb_requests.keys():
            raise RuntimeError('Recieved inform for request_id(%s), but no '
                               'such stored request.' % request_id)
        self._nb_requests[request_id].got_inform(msg.copy())

    def nb_request(self, request, inform_cb=None, reply_cb=None, *args):
        """
        Make a non-blocking request.
        :param self - this object.
        :param request - the request string.
        :param inform_cb - an optional callback function, called upon receipt
        of every inform to the request.
        :param reply_cb - an optional callback function, called upon receipt
        of the reply to the request.
        :param args - arguments to the katcp.Message object.
        """
        if len(self._nb_requests) == self._nb_max_requests:
            oldreq = self.nb_pop_oldest_request()
            LOGGER.debug('Request list full, removing oldest one(%s,%s).' % (
                oldreq.request, oldreq.request_id))
        request_id = self.nb_get_next_request_id()
        self.nb_add_request(request, request_id, inform_cb, reply_cb)
        request_msg = Message.request(request, *args)
        self._nb_request_func(msg=request_msg, reply_cb=self.nb_replycb,
                              inform_cb=self.nb_informcb, user_data=request_id)
        return {'host': self.host, 'request': request, 'id': request_id}


class AsyncRequest(object):
    """
    A class to hold information about a specific KATCP request made by a FPGA.
    """
    def __init__(self, host, request, request_id,
                 inform_cb=None, reply_cb=None):
        self.host = host
        self.request = request
        self.request_id = request_id
        self.time_tx = time.time()
        self.informs = []
        self.inform_times = []
        self.reply = None
        self.reply_time = -1
        self.reply_cb = reply_cb
        self.inform_cb = inform_cb

    def __str__(self):
        """

        :return:
        """
        return '%s(%s)@(%10.5f) - reply%s - informs(%i)' % (
            self.request, self.request_id, self.time_tx,
            str(self.reply), len(self.informs))

    def got_reply(self, reply_message):
        """

        :param reply_message:
        :return:
        """
        if not reply_message.name == self.request:
            error_string = 'rx reply(%s) does not match request(%s)' % (
                reply_message.name, self.request)
            LOGGER.error(error_string)
            raise RuntimeError(error_string)
        self.reply = reply_message
        self.reply_time = time.time()
        if self.reply_cb is not None:
            self.reply_cb(self.host, self.request_id)

    def got_inform(self, inform_message):
        """

        :param inform_message:
        :return:
        """
        if self.reply is not None:
            _errmsg = 'Received inform for message(%s,%s) after reply. ' \
                      'Invalid?' % (self.request, self.request_id)
            LOGGER.error(_errmsg)
            raise RuntimeError(_errmsg)
        if not inform_message.name == self.request:
            _errmsg = 'rx inform(%s) does not match request(%s)' % (
                inform_message.name, self.request)
            LOGGER.error(_errmsg)
            raise RuntimeError(_errmsg)
        self.informs.append(inform_message)
        self.inform_times.append(time.time())
        if self.inform_cb is not None:
            self.inform_cb(self.host, self.request_id)

    def complete_ok(self):
        """
        Has this request completed successfully?
        :return:
        """
        if self.reply is None:
            return False
        return self.reply.arguments[0] == Message.OK

# pylint: disable-msg=C0103
# pylint: disable-msg=C0301

import logging
LOGGER = logging.getLogger(__name__)

import threading
import time

from katcp import Message


class AsyncRequester(object):
    """A class to hold information about a specific KATCP request made by a Fpga.
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
        try:
            return self._nb_requests[request_id]
        except KeyError:
            return None

    def nb_pop_request_by_id(self, request_id):
        try:
            self._nb_requests_lock.acquire()
            r = self._nb_requests.pop(request_id)
            self._nb_requests_lock.release()
            return r
        except KeyError:
            return None

    def nb_pop_oldest_request(self):
        req = self._nb_requests[self._nb_requests.keys()[0]]
        for v in self._nb_requests.itervalues():
            if v.time_tx < req.time_tx:
                req = v
        self._nb_requests_lock.acquire()
        r = self.nb_pop_request_by_id(req.request_id)
        self._nb_requests_lock.release()
        return r

    def nb_get_request_result(self, request_id):
        req = self.nb_get_request_by_id(request_id)
        return req.reply, req.informs

    def nb_add_request(self, request_name, request_id, inform_cb, reply_cb):
        if request_id in self._nb_requests.keys():
            raise RuntimeError('Trying to add request with id(%s) but it already exists.' % request_id)
        self._nb_requests_lock.acquire()
        self._nb_requests[request_id] = AsyncRequest(self.host, request_name, request_id, inform_cb, reply_cb)
        self._nb_requests_lock.release()

    def nb_get_next_request_id(self):
        self._nb_request_id_lock.acquire()
        self._nb_request_id += 1
        reqid = self._nb_request_id
        self._nb_request_id_lock.release()
        return str(reqid)

    def nb_replycb(self, msg, *userdata):
        """The callback for request replies. Check that the ID exists and call that request's got_reply function.
           """
        request_id = ''.join(userdata)
        if request_id not in self._nb_requests.keys():
            raise RuntimeError('Recieved reply for request_id(%s), but no such stored request.' % request_id)
        self._nb_requests[request_id].got_reply(msg.copy())

    def nb_informcb(self, msg, *userdata):
        """The callback for request informs. Check that the ID exists and call that request's got_inform function.
           """
        request_id = ''.join(userdata)
        if request_id not in self._nb_requests.keys():
            raise RuntimeError('Recieved inform for request_id(%s), but no such stored request.' % request_id)
        self._nb_requests[request_id].got_inform(msg.copy())

    def nb_request(self, request, inform_cb=None, reply_cb=None, *args):
        """Make a non-blocking request.

           @param self          This object.
           @param request       The request string.
           @param inform_cb     An optional callback function, called upon receipt of every inform to the request.
           @param inform_cb     An optional callback function, called upon receipt of the reply to the request.
           @param args          Arguments to the katcp.Message object.
           """
        if len(self._nb_requests) == self._nb_max_requests:
            oldreq = self.nb_pop_oldest_request()
            LOGGER.info("Request list full, removing oldest one(%s,%s).", oldreq.request, oldreq.request_id)
            print "Request list full, removing oldest one(%s,%s)." % (oldreq.request, oldreq.request_id)
        request_id = self.nb_get_next_request_id()
        self.nb_add_request(request, request_id, inform_cb, reply_cb)
        self._nb_request_func(msg=Message.request(request, *args), reply_cb=self.nb_replycb,
                              inform_cb=self.nb_informcb, user_data=request_id)
        return {'host': self.host, 'request': request, 'id': request_id}


class AsyncRequest(object):
    """A class to hold information about a specific KATCP request made by a Fpga.
       """
    def __init__(self, host, request, request_id, inform_cb=None, reply_cb=None):
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
        return '%s(%s)@(%10.5f) - reply%s - informs(%i)' % (self.request, self.request_id, self.time_tx,
                                                            str(self.reply), len(self.informs))

    def got_reply(self, reply_message):
        if not reply_message.name == self.request:
            error_string = 'rx reply(%s) does not match request(%s)' % (reply_message.name, self.request)
            print error_string
            raise RuntimeError(error_string)
        self.reply = reply_message
        self.reply_time = time.time()
        if self.reply_cb is not None:
            self.reply_cb(self.host, self.request_id)

    def got_inform(self, inform_message):
        if self.reply is not None:
            LOGGER.error('Received inform for message(%s,%s) after reply. Invalid?', self.request, self.request_id)
            raise RuntimeError('Received inform for message(%s,%s) after reply. Invalid?' % (self.request,
                                                                                             self.request_id))
        if not inform_message.name == self.request:
            error_string = 'rx inform(%s) does not match request(%s)' % (inform_message.name, self.request)
            print error_string
            raise RuntimeError(error_string)
        self.informs.append(inform_message)
        self.inform_times.append(time.time())
        if self.inform_cb is not None:
            self.inform_cb(self.host, self.request_id)

    def complete_ok(self):
        """Has this request completed successfully?
        """
        if self.reply is None:
            return False
        return self.reply.arguments[0] == Message.OK

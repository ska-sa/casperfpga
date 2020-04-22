import logging
import struct
import time
import redis
import json
import tftpy
import base64
from numpy import random
from io import StringIO

from queue import Queue
from threading import Thread

from .transport_tapcp import TapcpTransport

__author__ = 'jackh'
__date__ = 'May 2019'

LOGGER = logging.getLogger(__name__)
REDIS_COMMAND_CHANNEL = "casperfpga:command"
REDIS_RESPONSE_CHANNEL = "casperfpga:response"

FAIL = False
SUCCESS = True

class RedisTftp(object):
    """
    # A class-wide variable to hold redis connections.
    # This prevents multiple instances of this class
    # from creating lots and lots (and lots) of redis connections
    """
    redis_pool = {}
    redis_conn = {}

    def __init__(self, redishost, host):
        """
        Initialized a redis PUBSUB connection
        :param host: IP Address of the targeted Board
        :param redishost: IP address of the redis gateway
        :return: none
        """

        if redishost not in RedisTftp.redis_pool.keys():
            RedisTftp.redis_pool[redishost] = redis.ConnectionPool(host=redishost, port=6379, db=0)
        if redishost not in RedisTftp.redis_conn.keys():
            RedisTftp.redis_conn[redishost] = redis.Redis(redishost, connection_pool=RedisTftp.redis_pool[redishost])
        self.r = RedisTftp.redis_conn[redishost]
        # Every instance gets its own PubSub object to make sure that multiple
        # RedisTftp instances can be threaded.
        # These don't close when the RedisTftp object is deallocated,
        # so they're manually closed in a `__del__` method
        self.resp_chan = self.r.pubsub()
        self.resp_chan.subscribe(REDIS_RESPONSE_CHANNEL)
        self._logger = LOGGER
        self.host = host
    
    def __del__(self):
        self.resp_chan.unsubscribe()
        self.resp_chan.close()
   
    def download(self, fname, buf, timeout):
        """
        :param fname (string):  File to be downloaded
        :param buf (StringIO):  Buffer into which file contents will be written
        :param timeout (float): Timeout in seconds
        """
        cmd = {
            "type" : "read",
            "target" : self.host,
            "file" : fname,
            "timeout" : timeout,
            "id"   : random.randint(2**31),
        }
        sent_message = self._send_message(cmd)
        response = self._get_response(sent_message, timeout=2*timeout)
        buf.write(response)

    def upload(self, fname, buf, timeout):
        """
        :param fname (string):  File to be uploaded
        :param buf (StringIO):  Buffer from which to read data
        :param timeout (float): Timeout in seconds
        """
        cmd = {
            "type" : "write",
            "target" : self.host,
            "file" : fname,
            "data" : base64.b64encode(buf.getvalue()),
            "timeout" : timeout,
            "id"   : random.randint(2**31),
        }

        sent_message = self._send_message(cmd)
        response = self._get_response(sent_message, timeout=2*timeout)
        
        
    def _send_message(self, command):
        """
        Send a command to the correlator via the corr:message
        pub-sub channel
        Args:
            command: correlator command
            **kwargs: optional arguments for this command
        
        Returns:
            correlator response to this command
        """
        message = json.dumps({"command":command, "time":time.time()})
        listeners = self.r.publish(REDIS_COMMAND_CHANNEL, message)
        if listeners == 0:
            self._logger.error("Sent command %s but no-one is listening!" % command)
            return None
        else:
            return message 

    def _get_response(self, command, timeout=10):
        """
        Get the correlator's response to `command` issued
        at `time`.
        Args:
            command: The command (JSON string) issued to the correlator.
            timeout: How many seconds to wait for a correlator response.
       
        Returns:
            Whatever the correlator returns for the given command
        """
        try:
            sent_message = json.loads(command)
        except:
            self._logger.error("Failed to decode sent command")
        target_time = sent_message["time"]
        target_id  = sent_message["command"]["id"]
        # This loop only gets activated if we get a response which
        # isn't for us.
        while(True):
            message = self.resp_chan.get_message(timeout=1+timeout)
            if message is not None and message["type"] != "message":
                continue
            if message is None:
                self._logger.error("Timed out waiting for a correlator response")
                raise RuntimeError("Timed out waiting for a correlator response")
                return
            try:
                message = json.loads(message["data"])   
            except:
                self._logger.error("Got a non-JSON message on the correlator response channel")
                raise RuntimeError("Got a non-JSON message on the correlator response channel")
                continue
            if ((message["id"] == target_id) and (message["time"] == target_time)):
                self._logger.debug("Got our redis response")
                if message["status"] != SUCCESS:
                    self._logger.info("Command failed!")
                    raise RuntimeError("Command failed!")
                if message["response"] is None:
                    return
                else:
                    return base64.b64decode(message["response"])
            else:
                self._logger.debug("Got a redis response which wasn't ours")

class RedisTapcpTransport(TapcpTransport):
    """
    Like a TapcpTransport but use a redis gateway instead of a tftp target
    """
    def __init__(self, **kwargs):
        """
        :param host (string): hostname of FPGA target
        :param redishost (string): hostname of redis gateway
        """
        TapcpTransport.__init__(self, **kwargs)
        self.t = RedisTftp(kwargs["redishost"], kwargs["host"])

class RedisTapcpDaemon(object):
    def __init__(self, redishost):
        """
        Initialized a redis PUBSUB connection
        :param redishost: IP address of the redis gateway
        :return: none
        """
        self.r = redis.Redis(redishost, max_connections=100)
        self.cmd_chan = self.r.pubsub()
        self.cmd_chan.subscribe(REDIS_COMMAND_CHANNEL)
        self._logger = LOGGER
        self.timeout = 1
        self.tftp_connections = {}
        # Queues to store transactions involving different FPGA boards
        self.hostq = {} # separate queue for each new board
        self.workers = {} # separate thread for each new board
    
    def run(self):
        while True:
            self._process_command()

    def _process_command(self):
        message_raw = self.cmd_chan.get_message(timeout=self.timeout, ignore_subscribe_messages=True)
        if message_raw is None:
            return
        try:
            message = json.loads(message_raw["data"])
        except:
            self._logger.warning("Got a non-JSON command!")
            return

        self._logger.info("Got command %s" % message_raw["data"])
        command = message["command"]
        host = command["target"]
        cmd_type = command["type"]
        filename = command["file"]
        timeout = command["timeout"]
        response = {"time": message["time"], "id": command["id"]}
        if host not in self.hostq.keys():
            self._logger.debug("Initializing queue for %s" % host)
            self.hostq[host] = Queue()
            self.workers[host] = Thread(target=self._process_queue, args=(self.hostq[host],host))
            self.workers[host].setDaemon(True)
            self.workers[host].start()
        self._logger.debug("Queuing task ID %d for host %s" % (command["id"], host))
        self.hostq[host].put(message)
            

    def _process_queue(self, q, host):
        self._logger.debug("Initializing TFTP connection to %s" % host)
        conn = tftpy.TftpClient(host, 69)
        while True:
            message = q.get()
            command = message["command"]
            host = command["target"]
            cmd_type = command["type"]
            filename = command["file"]
            timeout = command["timeout"]
            response = {"time": message["time"], "id": command["id"]}
            if cmd_type == "read":
                self._logger.debug("Processing read command (ID %d)" % command["id"])
                self.process_read_cmd(filename, timeout, response, conn)
            elif cmd_type == "write":
                self._logger.debug("Processing write command (ID %d)" % command["id"])
                data = command["data"]
                self.process_write_cmd(filename, timeout, response, conn, data)
            self._logger.debug("Marking task %d done" % command["id"])
            q.task_done()

    def process_read_cmd(self, filename, timeout, response, conn):
        try:
            buf = StringIO()
            conn.download(filename, buf, timeout=timeout)
            response["response"] = base64.b64encode(buf.getvalue())
            response["status"] = SUCCESS
            self.r.publish(REDIS_RESPONSE_CHANNEL, json.dumps(response))
        except:
            self._logger.error("Error on read!")
            response["response"] = ""
            response["status"] = FAIL
            self.r.publish(REDIS_RESPONSE_CHANNEL, json.dumps(response))
            try:
                conn.context.end()
            except:
                pass
        return

    def process_write_cmd(self, filename, timeout, response, conn, data):
        try:
            buf = StringIO(base64.b64decode(data))
            self._logger.info("Writing %d bytes" % buf.len)
            conn.upload(filename, buf, timeout=timeout)
            response["response"] = None
            response["status"] = SUCCESS
            self.r.publish(REDIS_RESPONSE_CHANNEL, json.dumps(response))
        except:
            self._logger.error("Error on write!")
            response["response"] = None
            response["status"] = FAIL
            self.r.publish(REDIS_RESPONSE_CHANNEL, json.dumps(response))
            try:
                conn.context.end()
            except:
                pass
        return

import logging
import struct
import time
import redis
import json
import tftpy
import base64
from numpy import random
from StringIO import StringIO

from transport_tapcp import TapcpTransport

__author__ = 'jackh'
__date__ = 'May 2019'

LOGGER = logging.getLogger(__name__)
REDIS_COMMAND_CHANNEL = "casperfpga:command"
REDIS_RESPONSE_CHANNEL = "casperfpga:response"

class RedisTftp(object):
    """
    # A class-wide variable to hold redis connections.
    # This prevents multiple instances of this class
    # from creating lots and lots (and lots) of redis connections
    """
    redis_connections = {}
    response_channels = {}

    def __init__(self, redishost, host):
        """
        Initialized a redis PUBSUB connection
        :param host: IP Address of the targeted Board
        :param redishost: IP address of the redis gateway
        :return: none
        """

        # If the redishost is one we've already connected to, use it again.
        # Otherwise, add it.
        # Also share response channels. This opens the door to all sorts of
        # unintended consequences if you try to multithread access to
        # multiple HeraCorrCM instances in the same program. But in most cases
        # sharing means the code will just do The Right Thing, and won't leave
        # a trail of a orphaned connections.
        if redishost not in self.redis_connections.keys():
            self.redis_connections[redishost] = redis.Redis(redishost, max_connections=100)
            self.response_channels[redishost] = self.redis_connections[redishost].pubsub()
            self.response_channels[redishost].subscribe(REDIS_RESPONSE_CHANNEL)
        self.r = self.redis_connections[redishost]
        self.resp_chan = self.response_channels[redishost]
        self._logger = LOGGER
        self.host = host
   
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
        target_cmd  = sent_message["command"]
        # This loop only gets activated if we get a response which
        # isn't for us.
        while(True):
            message = self.resp_chan.get_message(timeout=timeout)
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
            if ((message["command"] == target_cmd) and (message["time"] == target_time)):
                if message["response"] is None:
                    return
                else:
                    return base64.b64decode(message["response"])

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
    
    def run(self):
        while True:
            self._process_command()

    def _process_command(self):
        message = self.cmd_chan.get_message(timeout=self.timeout, ignore_subscribe_messages=True)
        if message is None:
            return
        try:
            message = json.loads(message["data"])
        except:
            self._logger.warning("Got a non-JSON command!")
            return
        #try:
        command = message["command"]
        host = command["target"]
        cmd_type = command["type"]
        filename = command["file"]
        timeout = command["timeout"]
        if host not in self.tftp_connections.keys():
            self.tftp_connections[host] = tftpy.TftpClient(host, 69)
        
        if cmd_type == "read":
            try:
                buf = StringIO()
                self.tftp_connections[host].download(filename, buf, timeout=timeout)
                message["response"] = base64.b64encode(buf.getvalue())
                self.r.publish(REDIS_RESPONSE_CHANNEL, json.dumps(message))
            except:
                self._logger.error("Error on read!")
                try:
                    self.tftp_connections[host].context.end()
                except:
                    pass
            return
        if cmd_type == "write":
            try:
                buf = StringIO(base64.b64decode(command["data"]))
                self.tftp_connections[host].upload(filename, buf, timeout=timeout)
                message["response"] = None
                self.r.publish(REDIS_RESPONSE_CHANNEL, json.dumps(message))
            except:
                self._logger.error("Error on write!")
                try:
                    self.tftp_connections[host].context.end()
                except:
                    pass
            return

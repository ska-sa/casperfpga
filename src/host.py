# pylint: disable-msg=C0103
# pylint: disable-msg=C0301
"""
Created on Feb 28, 2013

@author: paulp
"""


import logging
LOGGER = logging.getLogger(__name__)

from misc import log_not_implemented_error


class Host(object):
    """
    A processing host - Roach board, PC, etc. Hosts processing engines and communicates via a TCP/IP network.
    """
    def __init__(self, host, katcp_port):
        """Constructor
        @param host: the unique hostname/identifier for this Host
        @param katcp_port: and its KATCP port.
        """
        self.host = host
        self.katcp_port = katcp_port
        self.engines = {}

    def initialise(self):
        """Initialise this node to its normal running state.
        """
        log_not_implemented_error(LOGGER, '%s.initialise() not implemented' % self.host)

    def ping(self):
        """All hosts must supply a ping method that returns true or false.
        @return: True or False
        """
        log_not_implemented_error(LOGGER, '%s.ping() not implemented' % self.host)

    def is_running(self):
        """All hosts must supply a is_running method that returns true or false.
        @return: True or False
        """
        log_not_implemented_error(LOGGER, '%s.is_running() not implemented' % self.host)
    
    def get_config_file_info(self):
        """All hosts must supply a get_config_file_info method returning information on the config file
        currently running.
        @return name: name of file
        @return build_time: time file was built
        """
        log_not_implemented_error(LOGGER, '%s.config_file_info() not implemented' % self.host)
    
    def add_engine(self, new_engine):
        """Add an engine to this node.
        @param new_engine: the Engine object to add to this Host.
        """
        log_not_implemented_error(LOGGER, '%s.add_engine() not implemented'%self.host)

    def get_engine(self, engine_class, engine_id=None):
        """Get an engine based on engine_id and engine_class. If no engine_id is passed, all engines of the
        given type will be returned.
        @param engine_id: the unique id of the engine to return.
        @param engine_class: the engine class to look for.
        """
        log_not_implemented_error(LOGGER, '%s.get_engine() not implemented'%self.host)

    def __str__(self):
        return '%s@%s' % (self.host, self.katcp_port)
# end

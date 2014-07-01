"""
Created on Feb 28, 2013

@author: paulp
"""

import logging
LOGGER = logging.getLogger(__name__)


class KatAdc(object):
    """Information above KatAdc yellow blocks.
    """
    def __init__(self, parent, name):
        """
        @param parent: The owner of this block.
        @param name: The name of this block.
        """
        self.parent = parent
        self.name = name
        self.options = {}
        LOGGER.info('New KatADC %s', self.name)

# end

# pylint: disable-msg=C0103
# pylint: disable-msg=C0301
"""
Miscellaneous functions that are used in a few places but don't really belong
anywhere.
"""

import logging

LOGGER = logging.getLogger(__name__)


def log_runtime_error(log, error_string):
    """Write an error string to the given log file and then raise a runtime error.
    """
    try:
        log.error(error_string)
    except AttributeError:
        pass
    raise RuntimeError(error_string)


def log_io_error(log, error_string):
    """Write an error string to the given log file and then raise an io error.
    """
    try:
        log.error(error_string)
    except AttributeError:
        pass
    raise IOError(error_string)


def log_value_error(log, error_string):
    """Write an error string to the given log file and then raise a value error.
    """
    try:
        log.error(error_string)
    except AttributeError:
        pass
    raise ValueError(error_string)


def log_not_implemented_error(log, error_string):
    """Write an error string to the given log file and then raise a not implemented error.
    """
    try:
        log.error(error_string)
    except AttributeError:
        pass
    raise NotImplementedError(error_string)
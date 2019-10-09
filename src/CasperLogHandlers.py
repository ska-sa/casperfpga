import logging
import termcolors
import datetime
import os

LOGGER = logging.getLogger(__name__)

stream_handler = logging.StreamHandler()
# stream_handler.setLevel(logging.ERROR)
log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
stream_handler.setFormatter(log_formatter)
LOGGER.addHandler(stream_handler)
LOGGER.setLevel(logging.ERROR)


# region -- Custom getLogger commands --

def getLogger(*args, **kwargs):
    """
    Custom method allowing us to add default handlers to a logger

    :param logger_name: Mandatory, logger needs to have a name!
    :param log_level: All Instrument-level entities log at logging.DEBUG
                    - All Board-level entities log at logging.ERROR
    :return: Tuple 
            
            * Boolean Success/Fail, True/False
            * Logger entity with ConsoleHandler added as default
    """
    try:
        logger_name = kwargs['name']
    except KeyError:
        # warningmsg = 'Cannot instantiate a logger without a name!'
        # LOGGER.warning(warningmsg)
        # return False, None
        logger_name = 'testLogger'
    try:
        log_level = kwargs['log_level']
    except KeyError:
        log_level = logging.ERROR

    logger = logging.getLogger(logger_name)

    if logger.handlers:
        # logger has handlers already... ?
        # logger.setLevel(log_level)
        return False, logger
    else:
        console_handler = CasperConsoleHandler(name=logger_name)
        logger.addHandler(console_handler)

    logger.setLevel(log_level)
    return True, logger


def getNewLogger(*args, **kwargs):
    """
    Custom method allowing us to add default handlers to a logger

    :return: Tuple 

            * Boolean Success/Fail, True/False
            * Logger entity with FileHandler added as default
    """
    try:
        logger_name = kwargs['name']
    except KeyError:
        logger_name = 'testLogger'
    try:
        log_level = kwargs['log_level']
    except KeyError:
        log_level = logging.DEBUG

    logger = logging.getLogger(logger_name)

    if logger.handlers:
        # We can remove them
        # - If we instantiate a logger with the same name
        #   it will still maintain 'object ID'
        # logger.handlers = []

        # Yes, isinstance(handler, logging.HandlerType),
        # but it isn't working as expected
        logger.handlers = [handler for handler in logger.handlers if type(handler) != logging.StreamHandler]

    # Now add the FileHandler
    filename = '{}.log'.format(logger_name)
    file_handler = logging.FileHandler(filename)
    formatted_datetime = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-4]
    formatted_string = '%(name)s - ' + formatted_datetime + ' - %(levelname)s ' \
                        '| %(filename)s:%(lineno)d - %(msg)s'
    file_handler.setFormatter(logging.Formatter(formatted_string))
    logger.addHandler(file_handler)
    logger.setLevel(log_level)

    return True, logger

# endregion


# region -- CasperConsoleHandler --

class CasperConsoleHandler(logging.Handler):
    """
    Stream Log Handler for casperfpga records 

    * Trying a custom logger before incorporating into corr2
    * This inherits from the logging.Handler - Stream or File
    """

    def __init__(self, name, *args, **kwargs):
        """
        New method added to test logger functionality across transport layers
        
        * Need to add handlers for both Stream AND File

        :param name: Name of the StreamHandler
        :type name: str
        :param max_len: How many log records to store in the FIFO
        """
        # logging.Handler.__init__(self)
        super(CasperConsoleHandler, self).__init__(*args, **kwargs)

        # This always needs to be present
        self.name = name

        try:
            self._max_len = kwargs['max_len']
        except KeyError:
            self._max_len = 1000

        self._records = []

    def emit(self, record):
        """
        Handle a log record
        
        :param record: Log record as a string
        :return: True/False = Success/Fail
        """
        if len(self._records) >= self._max_len:
            self._records.pop(0)

        self._records.append(record)

        if record.exc_info:
            print termcolors.colorize('%s: %s Exception: ' % (record.name, record.msg), record.exc_info[0:-1],
                                      fg='red')
        else:
            console_text = self.format(record)
            if record.levelno == logging.DEBUG:
                print termcolors.colorize(console_text, fg='white')
            elif (record.levelno > logging.DEBUG) and (record.levelno < logging.WARNING):
                print termcolors.colorize(console_text, fg='green')
            elif (record.levelno >= logging.WARNING) and (record.levelno < logging.ERROR):
                print termcolors.colorize(console_text, fg='yellow')
            elif record.levelno >= logging.ERROR:
                print termcolors.colorize(console_text, fg='red')
            else:
                print '%s: %s' % (record.name, record.msg)

    def format(self, record):
        """
        :param record: Log record as a string, of type logging.LogRecord
        :return: Formatted record
        """
        formatted_datetime = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-4]
        formatted_string = '{} {} {} {}:{} - {}'.format(formatted_datetime, record.levelname, record.name,
                                                        record.filename, str(record.lineno), record.msg)
        
        return formatted_string

    def clear_log(self):
        """
        Clear the list of stored log messages
        """
        self._records = []

    def set_max_len(self, max_len):
        """

        :param max_len:
        """
        self._max_len = max_len

    def get_log_strings(self, num_to_print=1):
        """
        Get all log messages in FIFO associated with a logger entity
        :param num_to_print:
        """
        log_list = []
        for ctr, record in enumerate(self._records):
            if ctr == num_to_print:
                if record.exc_info:
                    log_list.append('%s: %s Exception: ' % (record.name, record.msg))
                else:
                    log_list.append('%s: %s' % (record.name, record.msg))
            pass
        return log_list

    def print_messages(self, num_to_print=1):
        """
        Print log messages stored in FIFO
        :param num_to_print:
        """

        for ctr, record in enumerate(self._records):
            if ctr == num_to_print:
                break
            if record.exc_info:
                print termcolors.colorize('%s: %s Exception: ' % (record.name, record.msg), record.exc_info[0:-1],
                                          fg='red')
            else:
                if record.levelno < logging.WARNING:
                    print termcolors.colorize('%s: %s' % (record.name, record.msg), fg='green')
                elif (record.levelno >= logging.WARNING) and (record.levelno < logging.ERROR):
                    print termcolors.colorize('%s: %s' % (record.name, record.msg), fg='yellow')
                elif record.levelno >= logging.ERROR:
                    print termcolors.colorize('%s: %s' % (record.name, record.msg), fg='red')
                else:
                    print '%s: %s' % (record.name, record.msg)

# endregion

# ----------------------------------------------------------------------------------------------
# ----------------------------------------------------------------------------------------------

# region -- Logger-related methods ---


def configure_console_logging(logger_entity, console_handler_name=None):
    """
    Method to configure logging to console using the casperfpga logging entity

    (A similar method exists in casperfpga)

    :param logger_entity: Logging entity to create and add the ConsoleHandler to
    :param console_handler_name: will use logger_entity.name by default
    :type console_handler_name: Optional
    """
    # Check if a log-handler with the specified name already exists
    if console_handler_name is None:
        # Use the name of the logger specified
        if logger_entity.name is None or logger_entity.name is '':
            # Problem!
            errmsg = 'Cannot have a logger without a name!'
            LOGGER.error(errmsg)
            return False
        # else: Continue
        console_handler_name = '{}_console'.format(logger_entity.name)
    # else: Do all the checks

    handlers = logger_entity.handlers
    for handler in handlers:
        # Check if there is already a StreamHandler with this name
        if hasattr(handler, 'baseFilename'):
            # It's a FileHandler, not a StreamHandler
            continue
        else:
            # StreamHandler (I hope)
            if handler.name.upper() == console_handler_name.upper():
                # Problem
                # LOGGER.warning('ConsoleHandler {} already exists'.format(console_handler_name))
                return False
                # raise ValueError('Cannot have multiple StreamHandlers '
                #                 'with the same name')
    # If it makes it out here, stream_name specified is fine

    console_handler = CasperConsoleHandler(name=console_handler_name)
    logger_entity.addHandler(console_handler)

    logger_entity.parent.handlers = []

    debugmsg = 'Successfully created ConsoleHandler {}'.format(console_handler_name)
    LOGGER.debug(debugmsg)

    return True


def configure_file_logging(logging_entity, filename=None, file_dir=None):
    """
    Method to configure logging to file using the casperfpga logging entity

    :param logging_entity: Logging entity to create and add the FileHandler to
    :param filename:
                    * must be in the format of filename.log
                    * Will default to casperfpga_{hostname}.log
    :type filename: Optional
    :param file_dir: must be a valid path
    :type file_dir: Optional
    """
    log_filename = None

    if filename:
        # Has user spec'd file directory as well?
        if file_dir:
            # First check if the directory exists
            abs_path = os.path.abspath(file_dir)
            if os.path.isdir(abs_path):
                log_filename = '{}/{}'.format(abs_path, filename)
            else:
                errmsg = '{} is not a valid directory'.format(file_dir)
                LOGGER.error(errmsg)
                raise ValueError(errmsg)
        else:
            # Store it in /tmp/
            log_filename = '/tmp/{}'.format(filename)
    else:
        log_filename = '/tmp/casperfpga_{}.log'.format(logging_entity.name)

    file_handler = logging.FileHandler(log_filename, mode='a')
    formatted_string = '%(asctime)s | %(levelname)s | %(name)s - %(filename)s:%(lineno)s - %(message)s'
    casperfpga_formatter = logging.Formatter(formatted_string)
    file_handler.setFormatter(casperfpga_formatter)
    logging_entity.addHandler(file_handler)

    LOGGER.info('Successfully enabled logging to file at {}'.format(log_filename))
    return True

# endregion

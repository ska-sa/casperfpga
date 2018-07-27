import logging
import termcolors
import datetime
import os

# from utils import get_kwarg

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.DEBUG)
stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.DEBUG)
LOGGER.addHandler(stream_handler)


def get_all_loggers():
    """
    Packaging a logging library function call, for testing
    :return: dictionary of logging objects
    """
    return logging.Logger.manager.loggerDict


def check_logging_level(logging_level):
    """
    Generic function to carry out a sanity check on the logging_level
    used to setup the logger
    :param logging_level: String input defining the logging_level:
                             Level      | Numeric Value
                             --------------------------
                             CRITICAL   | 50
                             ERROR      | 40
                             WARNING    | 30
                             INFO       | 20
                             DEBUG      | 10
                             NOTSET     | 0

    :return: Tuple - (Success/Fail, None/logging_level)
    """
    logging_level_numeric = getattr(logging, logging_level, None)
    if not isinstance(logging_level_numeric, int):
        # errmsg = 'Invalid Log Level: {}'.format(logging_level)
        # LOGGER.error(errmsg)
        return False, None
    # else: Continue
    return True, logging_level_numeric


# region -- CasperConsoleHandler --

class CasperConsoleHandler(logging.Handler):
    """
    Stream Log Handler for casperfpga messages
    - Trying a custom logger before incorporating into corr2
    - This inherits from the logging.Handler - Stream or File
    """

    def __init__(self, *args, **kwargs):
        """
        New method added to test logger functionality across transport layers
        - Need to add handlers for both Stream AND File
        :param stream_name: Name of the StreamHandler - string
        :param max_len: How many log messages to store in the FIFO
        :return:
        """
        # logging.Handler.__init__(self)
        super(CasperConsoleHandler, self).__init__()

        try:
            self.name = kwargs['name']
        except KeyError:
            # hostname is the logger.name anyway
            self.name = None
        try:
            self._max_len = kwargs['max_len']
        except KeyError:
            self._max_len = 1000

        self._records = []

    def set_name(self, name):
        """

        :param name:
        :return:
        """
        self.name = name
        return True

    def get_name(self):
        """

        :return:
        """
        return self.name

    def emit(self, message):
        """
        Handle a log message
        :param message: Log message as a string
        :return: True/False - Success/Fail
        """
        if len(self._records) >= self._max_len:
            self._records.pop(0)

        self._records.append(message)

        if message.exc_info:
            print termcolors.colorize('%s: %s Exception: ' % (message.name, message.msg), message.exc_info[0:-1],
                                      fg='red')
        else:
            # console_text = '{} | {}:{} - {}'.format(message.levelname, message.filename, str(message.lineno),
            #                                        message.msg)
            console_text = self.format(message)
            if message.levelno == logging.DEBUG:
                print termcolors.colorize(console_text, fg='white')
            elif (message.levelno > logging.DEBUG) and (message.levelno < logging.WARNING):
                print termcolors.colorize(console_text, fg='green')
            elif (message.levelno >= logging.WARNING) and (message.levelno < logging.ERROR):
                print termcolors.colorize(console_text, fg='yellow')
            elif message.levelno >= logging.ERROR:
                print termcolors.colorize(console_text, fg='red')
            else:
                print '%s: %s' % (message.name, message.msg)

    def format(self, record):
        """
        :param record: Log message as a string, of type logging.LogRecord
        :return: Formatted message
        """
        formatted_datetime = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-4]
        formatted_string = '{} {} {} {}:{} - {}'.format(formatted_datetime, record.levelname, record.name,
                                                              record.filename, str(record.lineno), record.msg)
        
        return formatted_string

    def clear_log(self):
        """
        Clear the list of stored log messages
        :return:
        """
        self._records = []

    def set_max_len(self, max_len):
        """

        :param max_len:
        :return:
        """
        self._max_len = max_len

    def get_log_strings(self, num_to_print=1):
        """
        Get all log messages in FIFO associated with a logger entity
        :param num_to_print:
        :return:
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
        :return:
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
    - A similar method exists in casperfpga
    :param logger_entity: Logging entity to create and add the ConsoleHandler to
    :param console_handler_name: Optional - will use logger_entity.name by default
    :return:
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
        console_handler_name = logger_entity.name
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
                LOGGER.warning('ConsoleHandler {} already exists'.format(console_handler_name))
                return False
                # raise ValueError('Cannot have multiple StreamHandlers '
                #                 'with the same name')
    # If it makes it out here, stream_name specified is fine

    console_handler = CasperConsoleHandler(name=console_handler_name)
    logger_entity.addHandler(console_handler)

    debugmsg = 'Successfully created ConsoleHandler {}'.format(console_handler_name)
    LOGGER.debug(debugmsg)

    return True


def configure_file_logging(logging_entity, filename=None, file_dir=None):
    """
    Method to configure logging to file using the casperfpga logging entity
    :param logging_entity: Logging entity to create and add the FileHandler to
    :param filename: Optional parameter - must be in the format of filename.log
                                        - Will default to casperfpga_{hostname}.log
    :param file_dir: Optional parameter - must be a valid path
    :return:
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

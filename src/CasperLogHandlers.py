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

        formatted_datetime = str(datetime.datetime.now())
        formatted_string = '{name} - {0} | {levelname} | {filename}:{lineno} -' \
                           ' {msg}'.format(formatted_datetime, **record)

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

# region -- CasperFileHandler --


class CasperFileHandler(logging.Handler):
    """
    File Log Handler for casperfpga messages
    - Trying a custom logger before incorporating into corr2
    - This inherits from the logging.Handler - Stream or File
    """

    def __init__(self, *args, **kwargs):
        """
        New method added to test logger functionality across transport layers
        - Need to add handlers for both Stream AND File
        FileHandler needs a Filename to write to!
        :return:
        """

        # logging.Handler.__init__(self)
        super(CasperFileHandler, self).__init__()

        if len(args) > 0:
            try:
                kwargs['max_len'] = args[1]
            except IndexError:
                pass

        # max_len_fifo = get_kwarg('max_len', kwargs)
        if kwargs['max_len']:
            self._max_len = kwargs['max_len']
        else:
            self._max_len = 1000

        self._records = []

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
                print termcolors.colorize(console_text, fg='cyan')
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

        formatted_datetime = str(datetime.datetime.now())
        # formatted_string = '{} - {} | {} | {}:{} - {}'.format(record.name, formatted_datetime, record.levelname,
        #                                                       record.filename, str(record.lineno), record.msg)
        formatted_string = '{name} - {0} | {levelname} | {filename}:{lineno} -' \
                           ' {msg}'.format(formatted_datetime, **record)

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
                print termcolors.colorize('%s: %s Exception: ' % (record.name, record.msg), record.exc_info[0:-1], fg='red')
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

# region -- Casper IO Handler --

# class CasperRedirectLogger(object):
#     """
#     Object that redirects to logger instance
#     """
#     def __init__(self, logger, log_level=logging.INFO):
#         self.logger = logger
#         self.log_level = log_level
#         self.linebuf = ''
#
#     def write(self, buf):
#         for line in buf.rstrip().splitlines():
#             self.logger.log(self.log_level, line.rstrip())

# endregion

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
    if filename:
        # Has user spec'd file directory as well?
        if file_dir:
            # First check if the directory exists
            if os.path.isdir(file_dir):
                log_filename = file_dir + filename
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


def get_logger_group(logger_dict=None, group_name=None):
    """
    Method to fetch all logger entities that match the group_name specified
    :param logger_dict: Dictionary of loggers - {logger_name, logging_entity}
    :param group_name: String that is found in loggers to be fetched
    :return: Dictionary of logger entities whose keys match group_name
    """
    if group_name is None or group_name is '':
        # Problem
        errmsg = 'Logger group name cannot be empty'
        LOGGER.error(errmsg)
        return None
    if logger_dict is None:
        logger_dict = logging.Logger.manager.loggerDict
    keys = logger_dict.keys()

    logger_group = {}

    for value in keys:
        if value.find(group_name) >= 0:
            logger_group[value] = logger_dict[value]
            # else: pass

    return logger_group


def set_logger_group_level(logger_group, log_level=logging.DEBUG):
    """
    ** Take in log_level as an INTEGER **
    Method to set the log-level of a group of loggers
    :param logger_group: Dictionary of logger and logging entities
    :param log_level: Effectively of type integer E logging.{CRITICAL,ERROR,WARNING,DEBUG,INFO}
    :return: Boolean - Success/Fail - True/False
    """

    # First, error-check the log_level specified
    # result, log_level_numeric = check_logging_level(log_level)
    result = isinstance(log_level, int)
    if not result:
        # Problem
        errmsg = 'Error with log_level specified: {}'.format(log_level)
        LOGGER.error(errmsg)
        return False

    for logger_key, logger_value in logger_group.items():
        # logger_value.setLevel(log_level_numeric)
        logger_value.setLevel(log_level)

    debugmsg = 'Successfully updated log-level of {} SKARABs to {}'.format(str(len(logger_group)), log_level)
    LOGGER.debug(debugmsg)
    return True


def add_handler_to_loggers(logger_dict, log_handler):
    """
    Adds a log handler to a group of loggers
    :param logger_dict: dictionary of logger objects
    :param log_handler: log-handler specified/instantiated by the user
    :return: Boolean - True/False, Success/Fail
    """

    # Need to error-check that the log_handler specified is actually
    # of type logging.Handler
    if not hasattr(log_handler, 'emit'):
        # Impostor!
        errmsg = 'Log-handler specified is not of type logging.Handler. ' \
                 'Unable to add Handler {} to logger group'.format(log_handler)
        LOGGER.error(errmsg)
        return False

    for logger_key, logger_value in logger_dict.items():
        if not _add_handler_to_logger(logger_value, log_handler):
            # Problem
            return False
            # else: Continue
    debugmsg = 'Successfully added log_handler to group of {} loggers'.format(str(len(logger_dict)))
    LOGGER.debug(debugmsg)

    return True


def _add_handler_to_logger(logger, log_handler):
    """
    Abstracted method from adding log-handler to group to localise error-checking
    :param logger: logging entity
    :param log_handler: log-handler specified/instantiated by the user
    :return: Boolean - True/False, Success/Fail
    """
    # First check if the log_handler has already been added to the logger
    # Or if the logger already has a log-handler with the same name
    handlers = logger.handlers
    for handler in handlers:
        # ** We don't care what type of handler it is **
        # if hasattr(handler, 'baseFilename'):
        #     # It's a FileHandler, not a StreamHandler(/KatcpHandler)
        #     continue
        # else:
            # StreamHandler, probably
        if handler.name.upper() == log_handler.name.upper():
            # Problem
            errmsg = 'skarab "{}" have multiple log-handlers with ' \
                     'the same name: {}'.format(logger.name, log_handler.name)
            LOGGER.error(errmsg)
            return False
        # else: All good

    # Separate method to set the log-level
    logger.addHandler(log_handler)

    debugmsg = 'Successfully added log_handler to logger-{}'.format(logger.name)
    LOGGER.debug(debugmsg)
    return True


def remove_handler_from_loggers(logger_dict, log_handler):
    """
    Remove log_handler from logger_dict, should a logger in the group
    have said log_handler.
    :param logger_dict: Dictionary of logger objects
    :param log_handler: Actual log-handler entity?
    :return:
    """

    if len(logger_dict) < 1:
        # Problem
        errmsg = 'Logger group specified must contain at least one logger'
        LOGGER.error(errmsg)

    for logger_key, logger_value in logger_dict.items():
        if type(logger_value) is not logging.Logger:
            # Don't need it
            continue
        elif not _remove_handler_from_logger(logger_value, log_handler.name):
            # Problem
            errmsg = 'Failed to remove handler-{} from logger-{}'.format(logger_key, log_handler) # name)
            LOGGER.error(errmsg)
            return False

    return True


def get_log_handler_by_name(log_handler_name, logger_dict=None):
    """

    :param log_handler_name:
    :param logger_dict:
    :return: log_handler_return - Should be of type logging.Handler (at least parent)
    """

    # Sanity check on log_handler_name
    if log_handler_name is None or log_handler_name is '':
        # Problem
        errmsg = 'No log-handler name specified'
        LOGGER.error(errmsg)
        return False

    for logger_key, logger_value in logger_dict:
        if type(logger_value) is not logging.Logger:
            # Don't need it
            continue
        else:
            for handler in logger_value.handlers:
                # We stop when we find the first instance of this handler
                if handler.name.find(log_handler_name) >= 0:
                    # Found it
                    return handler


def _remove_handler_from_logger(logger, log_handler_name):
    """
    Removes handler from logging entity
    - Just easier to do it by name, rather than type
    :return:
    """
    # Because we can't act on the list we need to scroll through
    log_handlers = logger.handlers

    for handler in log_handlers:
        if handler.name.find(log_handler_name) > 0:
            # Nice
            logger.removeHandler(handler)

    return True


def remove_all_loggers(logger_dict=None):
    """

    :param logger_dict: Dictionary of loggers and their corresponding
                        logging entities
    :return: Boolean - Success/Fail - True/False
    """

    if logger_dict is None:
        logger_dict = logging.Logger.manager.loggerDict

    num_handlers = 0
    for logger_key, logger_value in logger_dict.items():
        num_handlers = len(logger_value.handlers)
        logger_value.handlers = []
        debugmsg = 'Successfully removed {} Handlers from ' \
                   'logger-{}'.format(num_handlers, logger_key)
        LOGGER.debug(debugmsg)

    return True

# endregion

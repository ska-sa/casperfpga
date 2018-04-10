import logging
import termcolors
import datetime

# from utils import get_kwarg


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

    :return:
    """
    logging_level_numeric = getattr(logging, logging_level, None)
    if not isinstance(logging_level_numeric, int):
        raise ValueError('Invalid Log Level: %s' % logging_level)
    # else: Continue
    return logging_level


# region -- CasperStreamHandler --
class CasperStreamHandler(logging.Handler):
    """
    Stream Log Handler for casperfpga messages
    - Trying a custom logger before incorporating into corr2
    - This inherits from the logging.Handler - Stream or File
    """

    def __init__(self, *args, **kwargs):
        """
        New method added to test logger functionality across transport layers
        - Need to add handlers for both Stream AND File
        :param max_len: How many log messages to store in the FIFO
        :return:
        """

        # logging.Handler.__init__(self)
        super(CasperStreamHandler, self).__init__()

        if len(args) > 0:
            try:
                kwargs['hostname'] = args[0]
                kwargs['max_len'] = args[1]
            except IndexError:
                pass

        self._host = kwargs['hostname']

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
        # formatted_string = '{} || {} - {} - {}'.format(formatted_datetime, record.name, 'temp', 'temp')
        # formatted_string = '{} | {} | {} - {}:{} - {}'.format(formatted_datetime, record.levelname, self._host,
        #                                                       record.filename, str(record.lineno), record.msg)
        formatted_string = '{} - {} | {} | {}:{} - {}'.format(record.name, formatted_datetime, record.levelname,
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
        # formatted_string = '{} || {} - {} - {}'.format(formatted_datetime, record.name, 'temp', 'temp')
        # formatted_string = '{} - {} | {} | {}:{} - {}'.format(self._host, formatted_datetime, record.levelname,
        #                                                      record.filename, str(record.lineno), record.msg)
        formatted_string = '{} - {} | {} | {}:{} - {}'.format(record.name, formatted_datetime, record.levelname,
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

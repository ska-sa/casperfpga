"""
Playing with ncurses in Python to scroll up and down, left and right,
through a list of data that is periodically refreshed.

Revs:
    **2010-12-11:**  JRM Added concat for status line to prevent bailing on small terminals.
    Code cleanup to prevent modification of external variables. Added left, right page controls
"""

import curses
import logging

# LOGGER = logging.getLogger(__name__)


def screen_teardown():
    """
    Restore sensible options to the terminal upon exit
    """
    logging.debug('Ncurses screen teardown')
    curses.nocbreak()
    curses.echo()
    curses.endwin()


class Screenline(object):
    def __init__(self, data, xpos, ypos, cr=True, fixed=False,
                 attributes=curses.A_NORMAL):
        """
        :param data: A String to be placed on the screen
        :param xpos: x position, -1 means at current xpos
        :param ypos: y position, -1 means at current ypos
        :param ypos: if True, start a new line after this one
        :param fixed: if True, always at this pos from top left, scrolling
            makes no difference
        :param attributes: Curses string attributes
        """
        assert type(data) == str
        self.data = data
        self.xpos = xpos
        self.ypos = ypos
        self.cr = cr
        self.fixed = fixed
        if not isinstance(attributes, list):
            attributes = [attributes]
        self.line_attributes = attributes
        self.changed = True

    def __repr__(self):
        return '"%s" len(%i) @ (%i,%i)%s' % (
            self.data, len(self.data), self.xpos, self.ypos,
            ' cr' if self.cr else ''
            ' fixed' if self.fixed else ''
        )


class Scroll(object):
    """
    Scrollable ncurses screen.
    """
    def __init__(self, debug=False):
        self._instruction_string = ''
        self._offset_y = 0
        self._offset_x = 0
        self._screen = None
        self._curr_y = 0
        # self._curr_x = 0
        self._sbuffer = []
        self._xmin = 0
        self._xmax = 0
        self._ymin = 0
        self._ymax = 0
        self._debugging = debug
        # LOGGER.debug('New Scroll() created.')

    # set up the screen
    def screen_setup(self):
        """
        Set up a curses screen object and associated options
        """
        self._screen = curses.initscr()
        self._screen.keypad(1)
        self._screen.nodelay(1)
        curses.noecho()
        curses.cbreak()
        height, width = self._screen.getmaxyx()
        self._ymax = height - 1
        self._xmax = width
        # LOGGER.debug('Scroll() set up - max x/y = %i/%i' % (
        #     self._xmax, self._ymax
        # ))

    def on_keypress(self):
        """
        Handle key presses.
        """
        key = self._screen.getch()
        if key > 0:
            try:
                key_char = chr(key)
            except ValueError:
                key_char = '_'
            if key == 259:
                self._offset_y -= 1               # up
            elif key == 258:
                self._offset_y += 1               # down
            elif key == 261:
                self._offset_x -= 1               # right
            elif key == 260:
                self._offset_x += 1               # left
            elif key_char == 'q':
                return [-1, 'q']
            elif key_char == 'u':
                self._offset_y -= self._ymax + 1
            elif key_char == 'd':
                self._offset_y += self._ymax + 1
            elif key_char == 'l':
                self._offset_x += self._xmax
            elif key_char == 'r':
                self._offset_x -= self._xmax
            elif key_char == 'h':
                self._offset_x = 0
                self._offset_y = 0
            # LOGGER.debug('[%i %s] keypress event' % (key, key_char))
            return [key, key_char]
        else:
            return [0, '_']

    def clear_screen(self):
        """
        Clear the ncurses screen.
        """
        self._screen.clear()

    def cr(self):
        """
        Carriage return, go to the next line
        """
        self._curr_y += 1

    def add_string(self, new_str, xpos=-1, ypos=-1, cr=False,
                   fixed=False, attributes=curses.A_NORMAL):
        """
        Add a string to a position on the screen.
        
        :param new_str:
        :param xpos:
        :param ypos:
        :param cr:
        :param fixed:
        :param attributes:
        """
        if fixed and ((xpos == -1) or (ypos == -1)):
            # LOGGER.error('Cannot have a fixed string with undefined position: '
            #              '"%s" @ (%i, %i) fixed' % (new_str, xpos, ypos))
            raise ValueError('Cannot have a fixed string with undefined '
                             'position')
        # LOGGER.debug('Added STR len(%i) to position (%i,%i) cr(%s) '
        #              'fixed(%s)' % (len(new_str), xpos, ypos,
        #                             'yes' if cr else 'no',
        #                             'yes' if fixed else 'no'))
        self._sbuffer.append(
            Screenline(new_str, xpos,
                       ypos if ypos > -1 else self._curr_y,
                       cr, fixed, attributes)
        )
        if cr:
            self._curr_y += 1
        return self._sbuffer[-1]

    def add_line(self, new_line, attributes=curses.A_NORMAL):
        """
        Add a text line to the screen buffer.

        :param new_line:
        :param attributes:
        """
        # LOGGER.debug('Added LINE len(%i) to line %i' % (
        #     len(new_line), self._curr_y))
        self._sbuffer.append(
            Screenline(new_line, 0, self._curr_y, True, False, attributes)
        )
        self._curr_y += 1
        return self._sbuffer[-1]

    def get_current_line(self):
        """
        Return the current y position of the internal screen buffer.
        """
        return self._curr_y

    def set_current_line(self, linenum):
        """
        Set the current y position of the internal screen buffer.

        :param linenum:
        """
        self._curr_y = linenum

    def _load_buffer_from_list(self, screendata):
        """
        Load the internal screen buffer from a given mixed list of
        strings and Screenlines.
        """
        if not isinstance(screendata, list):
            raise TypeError('Provided screen data must be a list!')
        self._sbuffer = []
        self._curr_y = 0
        for line in screendata:
            if not isinstance(line, Screenline):
                line = Screenline(line)
            self._sbuffer.append(line)
            self._curr_y += 1

    def _sbuffer_y_max(self):
        """
        Work out how many lines the sbuffer needs.
        """
        if len(self._sbuffer) == 0:
            return 0
        maxy = 1
        for sline in self._sbuffer:
            if sline.ypos == -1:
                # LOGGER.error('ypos of -1 makes no sense')
                raise RuntimeError('ypos of -1 makes no sense')
            maxy = max(maxy, sline.ypos)
        return maxy

    # def _calculate_screen_pos(self, sline):
    #     """
    #     Calculate the current screen position of a ScreenLine, given its
    #     properties.
    #     :param sline: a ScreenLine
    #     :return: (str_start, str_end), (str_xpos, str_ypos)
    #     """
    #     if sline.fixed:
    #         return (0, self._xmax), (sline.xpos, sline.ypos)
    #     xpos_shifted = sline.xpos + self._offset_x
    #     if xpos_shifted < 0:
    #         xpos = 0
    #         strs = xpos_shifted * -1
    #     else:
    #         xpos = xpos_shifted
    #         strs = 0
    #     stre = min(self._xmax, strs + len(sline.data))
    #     ypos = sline.ypos + self._offset_y
    #     return (strs, stre), (xpos, ypos)

    def draw_screen(self, data=None):
        """
        Draw the screen using the provided data
        TODO: ylimits, xlimits, proper line counts in the status
        """
        self._screen.clear()
        if data is not None:
            self._load_buffer_from_list(data)

        height, width = self._screen.getmaxyx()
        self._ymax = height - 1
        self._xmax = width - 1

        # LOGGER.debug('draw_screen:')
        # LOGGER.debug('\t%i ScreenLine items to process' % len(self._sbuffer))
        #
        # # debug, print(the lines to be drawn)
        # for sctr, sline in enumerate(self._sbuffer):
        #     LOGGER.debug('\t%i - %s' % (sctr, sline))
        #
        # # loop through lines, compute their new x and y pos and and write
        # # them to ncurses buffer
        # LOGGER.debug('xoff(%i) yoff(%i)' % (self._offset_x, self._offset_y))

        # work out relative positions
        ymax = 0
        curr_ypos = 0
        curr_xpos = 0
        positions = []
        for sctr, sline in enumerate(self._sbuffer):
            if sline.fixed:
                # fixed position on the screen always
                xpos = sline.xpos
                ypos = sline.ypos
                ymax = max(ymax, ypos)
                positions.append((xpos, ypos))
                continue
            if sline.xpos == -1:
                # tailing on from the last line
                xpos = curr_xpos
                ypos = curr_ypos if sline.ypos == -1 else sline.ypos
            else:
                # other lines
                xpos = sline.xpos
                ypos = curr_ypos if sline.ypos == -1 else sline.ypos
            positions.append((xpos, ypos))
            ymax = max(ymax, ypos)
            if sline.cr:
                curr_xpos = 0
                curr_ypos += 1
            else:
                curr_xpos += len(sline.data)

        # LOGGER.debug('Initial positions:')
        # for sctr, position in enumerate(positions):
        #     LOGGER.debug('\tstr_%i: %s' % (sctr, position))

        # shift them
        for sctr, sline in enumerate(self._sbuffer):
            if sline.fixed:
                continue
            pos = positions[sctr]
            newpos = (
                pos[0] + self._offset_x,
                pos[1] + self._offset_y,
            )
            positions[sctr] = newpos

        # LOGGER.debug('Shifted positions:')
        # for sctr, position in enumerate(positions):
        #     LOGGER.debug('\tstr_%i: %s' % (sctr, position))

        # truncate strings if necessary
        string_limits = []
        for sctr, sline in enumerate(self._sbuffer):
            pos = positions[sctr]
            str_start = 0
            str_end = len(sline.data)
            if pos[0] < 0:
                str_start = pos[0] * -1
            else:
                if pos[0] + str_end > self._xmax:
                    str_end = self._xmax - pos[0]
            if str_end < 0:
                str_end = 0
            string_limits.append((str_start, str_end))

        # LOGGER.debug('Truncated strings:')
        # for sctr, sline in enumerate(self._sbuffer):
        #     lims = string_limits[sctr]
        #     dstr = sline.data[lims[0]:lims[1]]
        #     LOGGER.debug('\tstr_%i: %s - %s' % (sctr, lims, dstr))

        # correct position of truncated strings
        for sctr, sline in enumerate(self._sbuffer):
            pos = positions[sctr]
            positions[sctr] = (
                max(0, pos[0]),
                pos[1]
            )
        # LOGGER.debug('Corrected positions:')
        # for sctr, position in enumerate(positions):
        #     LOGGER.debug('\tstr_%i: %s' % (sctr, position))

        # show them
        got_data = False
        for sctr, sline in enumerate(self._sbuffer):
            pos = positions[sctr]
            if pos[1] < 0:
                continue
            if pos[1] >= self._ymax:
                continue
            if pos[0] > self._xmax:
                continue
            # are there soft min limits?
            if not sline.fixed:
                if (self._xmin > 0) and (pos[0] < self._xmin):
                    continue
                if (self._ymin > 0) and (pos[1] < self._ymin):
                    continue
            str_lims = string_limits[sctr]
            drstr = sline.data[str_lims[0]:str_lims[1]]
            if len(drstr) == 0:
                continue
            try:
                got_data = True
                self._screen.addstr(pos[1], pos[0],
                                    drstr, *sline.line_attributes)
            except Exception as e:
                # LOGGER.error(
                #     'ERROR drawing str_%i - currx_y(%i,%i) - start_stop(%i,%i)'
                #     ' slinex_y(%i,%i) xpos_ypos(%i,%i) -> %s\n'
                #     'Exception: %s' % (
                #         sctr, curr_xpos, curr_ypos, str_lims[0], str_lims[1],
                #         sline.xpos, sline.ypos,
                #         pos[0], pos[1],
                #         drstr,
                #         e.message))
                continue
        if not got_data:
            if (self._offset_x != 0) or (self._offset_y != 0):
                drstr = '<no data onscreen - h to rehome>'
            else:
                drstr = '<no data>'
            if len(drstr) > self._xmax:
                drstr = drstr[0:self._xmax]
            self._screen.addstr(0, 0, drstr)
        stat_line = 'Row offset %i. Column offset %i. %s Scroll with arrow keys. \
        u, d, l, r = page up, down, left and right. h = home, q = quit.' %\
                    (self._offset_y * -1, self._offset_x,
                     self._instruction_string)
        stat_line = stat_line[0:self._xmax]
        self._screen.addstr(self._ymax, 0, stat_line, curses.A_REVERSE)
        self._screen.refresh()

    def clear_buffer(self):
        self._sbuffer = []
        self._curr_y = 0
        # self._curr_x = 0

    def set_xlimits(self, xmin=-1, xmax=-1):
        if xmin == -1 and xmax == -1:
            return
        if xmin > -1:
            self._xmin = xmin
        if xmax > -1:
            self._xmax = xmax

    def set_ylimits(self, ymin=-1, ymax=-1):
        if ymin == -1 and ymax == -1:
            return
        if ymin > -1:
            self._ymin = ymin
        if ymax > -1:
            self._ymax = ymax

    # def set_ypos(self, newpos):
    #     self._curr_y = newpos

    # set and get the instruction string at the bottom
    def get_instruction_string(self):
        return self._instruction_string

    def set_instruction_string(self, new_string):
        self._instruction_string = new_string

    # def draw_string(self, new_string, **kwargs):
    #     """
    #     Draw a new line to the screen, takes an argument as to whether the
    #     screen should be immediately refreshed or not
    #     """
    #     raise NotImplementedError
    #     try:
    #         refresh = kwargs.pop('refresh')
    #     except KeyError:
    #         refresh = False
    #     self._screen.addstr(self._curr_y, self._curr_x, new_string, **kwargs)
    #     if new_string.endswith('\n'):
    #         self._curr_y += 1
    #         self._curr_x = 0
    #     else:
    #         self._curr_x += len(new_string)
    #     if refresh:
    #         self._screen.refresh()

# end of file

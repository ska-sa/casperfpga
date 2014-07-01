# pylint: disable-msg=C0301
# pylint: disable-msg=E1101
"""
Playing with ncurses in Python to scroll up and down, left and right, through a list of data that is periodically refreshed.

Revs:
2010-12-11  JRM Added concat for status line to prevent bailing on small terminals.
                Code cleanup to prevent modification of external variables.
                Added left, right page controls
"""

import curses

def screen_teardown():
    '''Restore sensible options to the terminal upon exit
    '''
    curses.nocbreak()
    curses.echo()
    curses.endwin()

class Screenline(object):
    def __init__(self, data, xpos=-1, ypos=-1, absolute=False, attributes=curses.A_NORMAL):
        assert type(data) == str
        self.data = data
        self.xpos = xpos
        self.ypos = ypos
        self.absolute = absolute
        if not isinstance(attributes, list):
            attributes = [attributes]
        self.line_attributes = attributes

class Scroll(object):
    '''Scrollable ncurses screen.
    '''
    def __init__(self, debug=False):
        '''Constructor
        '''
        self._instruction_string = ''
        self._offset_y = 0
        self._offset_x = 0
        self._screen = None
        self._curr_y = 0
        self._curr_x = 0
        self._sbuffer = []
        self._xmin = 0
        self._xmax = 0
        self._ymin = 0
        self._ymax = 0
        self._debugging = debug

    # set up the screen
    def screen_setup(self):
        '''Set up a curses screen object and associated options
        '''
        self._screen = curses.initscr()
        self._screen.keypad(1)
        self._screen.nodelay(1)
        curses.noecho()
        curses.cbreak()
        self._ymax = curses.LINES - 1
        self._xmax = curses.COLS

    def on_keypress(self):
        '''
        Handle key presses.
        '''
        key = self._screen.getch()
        if key > 0:
            if key == 259:
                self._offset_y -= 1               # up
            elif key == 258:
                self._offset_y += 1               # down
            elif key == 261:
                self._offset_x -= 1               # right
            elif key == 260:
                self._offset_x += 1               # left
            elif chr(key) == 'q':
                return [-1, 'q']
            elif chr(key) == 'u':
                self._offset_y -= curses.LINES
            elif chr(key) == 'd':
                self._offset_y += curses.LINES
            elif chr(key) == 'l':
                self._offset_x += curses.COLS
            elif chr(key) == 'r':
                self._offset_x -= curses.COLS
            elif chr(key) == 'h':
                self._offset_x = 0
                self._offset_y = 0
            try:
                char = chr(key)
            except ValueError:
                char = '_'
            return [key, char]
        else:
            return [0, '_']

    def clear_screen(self):
        '''Clear the ncurses screen.
        '''
        self._screen.clear()

    def add_line(self, new_line, xpos=-1, ypos=-1, absolute=False, attributes=curses.A_NORMAL):
        '''Add a text line to the screen buffer.
        '''
        if not isinstance(new_line, str):
            raise TypeError('new_line must be a string!')
        yposition = ypos
        if yposition < 0:
            yposition = self._curr_y
            self._curr_y += 1
        self._sbuffer.append(Screenline(new_line, xpos, yposition, absolute, attributes))

    def get_current_line(self):
        '''Return the current y position of the internal screen buffer.
        '''
        return self._curr_y
    def set_current_line(self, linenum):
        '''Set the current y position of the internal screen buffer.
        '''
        self._curr_y = linenum

    def _load_buffer_from_list(self, screendata):
        '''Load the internal screen buffer from a given mixed list of
        strings and Screenlines.
        '''
        if not isinstance(screendata, list):
            raise TypeError('Provided screen data must be a list!')
        self._sbuffer = []
        for line in screendata:
            if not isinstance(line, Screenline):
                line = Screenline(line)
            self._sbuffer.append(line)

    def _sbuffer_y_max(self):
        '''Work out how many lines the sbuffer needs.
        '''
        maxy = 0
        for sline in self._sbuffer:
            if sline.ypos == -1:
                maxy += 1
            else:
                maxy = max(maxy, sline.ypos)
        return maxy

    def _calculate_screen_pos(self, sline, yposition):
        if sline.absolute:
            strs = 0
            stre = curses.COLS
            strx = sline.xpos
            stry = sline.ypos
        else:
            stringx = max(sline.xpos, 0) + self._offset_x
            if stringx < 0:
                xpos = 0
                strs = stringx * -1
            else:
                xpos = stringx
                strs = 0
            stre = strs + curses.COLS
            stry = sline.ypos
            if stry == -1:
                stry = yposition
                yposition += 1
            strx = xpos
            stry -= self._offset_y
        return (strs, stre, strx, stry, yposition)

    def draw_screen(self, data=None):
        '''Draw the screen using the provided data
        TODO: ylimits, xlimits, proper line counts in the status
        '''
        self._screen.clear()
        if data != None:
            self._load_buffer_from_list(data)
        num_lines_total = self._sbuffer_y_max()
        yposition = 0
        top_line = 0
        for sline in self._sbuffer:
            (strs, stre, strx, stry, yposition) = self._calculate_screen_pos(sline, yposition)
            drawstring = sline.data[strs : stre]
            if self._debugging:
                drawstring += '_(%d,%d,[%d:%d])' % (strx, stry, strs, stre)
            try:
                if sline.absolute:
                    self._screen.addstr(stry, strx, drawstring, *sline.line_attributes)
                elif (stry >= self._ymin) and (stry < self._ymax):
                    self._screen.addstr(stry, strx, drawstring, *sline.line_attributes)
                    top_line = self._offset_y - yposition
            except Exception, e:
                e.args = ('(%d,%d)_%s - ' % (stry, strx, drawstring) + e.args[0], )
                raise
            if yposition + self._offset_y >= self._ymax - 2:
                break
        if self._debugging:
            self._screen.addstr(self._ymax - 2, 0, 'offsets(%d,%d) dims(%d,%d) sbuf_ymax(%d) xlim(%d,%d) ylim(%d,%d)' %
                (self._offset_x, self._offset_y, curses.COLS, curses.LINES,
                num_lines_total, self._xmin, self._xmax, self._ymin, self._ymax))
        stat_line = 'Showing line %i to %i of %i. Column offset %i. %s Scroll with arrow keys. u, d, l, r = page up, down, left and right. h = home, q = quit.' % \
            (top_line, yposition, num_lines_total, self._offset_x,
             self._instruction_string)
        self._screen.addstr(curses.LINES - 1, 0, stat_line, curses.A_REVERSE)
        self._screen.refresh()

    def clear_buffer(self):
        self._sbuffer = []
        self._curr_y = 0
        self._curr_x = 0

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

    def set_ypos(self, newpos):
        self._curr_y = newpos

    # set and get the instruction string at the bottom
    def get_instruction_string(self):
        return self._instruction_string
    def set_instruction_string(self, new_string):
        self._instruction_string = new_string

    def draw_string(self, new_string, **kwargs):
        '''Draw a new line to the screen, takes an argument as to whether the screen should be immediately refreshed or not
        '''
        raise NotImplementedError
        try:
            refresh = kwargs.pop('refresh')
        except KeyError:
            refresh = False
        self._screen.addstr(self._curr_y, self._curr_x, new_string, **kwargs)
        if new_string.endswith('\n'):
            self._curr_y += 1
            self._curr_x = 0
        else:
            self._curr_x += len(new_string)
        if refresh:
            self._screen.refresh()

# end of file

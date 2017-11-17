import fcntl
import os
import tty
import termios
import struct
import sys
import traceback


DEBUGGING = False


class DebugFile(object):
    def __init__(self):
        super(DebugFile, self).__init__()
        self.fp = os.path.join(os.path.dirname(__file__), "debug.log")

    def write(self, msg):
        if DEBUGGING:
            with open(self.fp, "a") as fh:
                fh.writelines([msg + "\n"])


DEBUG = DebugFile()


class ANSI(object):
    ESCAPE = "\x1B"
    newline = "\r\n"
    CTRL_Q = "\x11"
    KEY_UP = "[A"
    KEY_DOWN = "[B"
    KEY_RIGHT = "[C"
    KEY_LEFT = "[D"


    @classmethod
    def clear_screen(cls):
        sys.stdout.write(
            cls.ESCAPE + "[2J"
        )

    @classmethod
    def move_cursor(cls, row, column):
        sys.stdout.write(
            cls.ESCAPE + "[{x};{y}H".format(
                x=row+1, y=column+1
            )
        )


class Editor(object):

    def __init__(self, path="test.txt"):
        super(Editor, self).__init__()
        with open(path, "rt") as fh:
            self.lines = map(self.strip_line_ending, fh.readlines())

        self.rows, self.columns = 0, 0
        self.buffer = Buffer(self.lines)
        self.cursor = Cursor()
        print(self.cursor)
        self.run()

    def strip_line_ending(self, line):
        return line.replace("\n", "")

    def run(self):
        while True:
            try:
                self.render()
                self.handle_input()
            except Exception:
                sys.stdout.write("\n" * 50)
                traceback.print_exc()
                break

    def size(self):
        rows, cols = struct.unpack(
            "hh",
            fcntl.ioctl(sys.stdin.fileno(), termios.TIOCGWINSZ, "1234")
        )
        return int(rows), int(cols)

    def getchar(self):
        # Returns a single character from standard input
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(sys.stdin.fileno())
            ch = sys.stdin.read(1)
        except Exception as err:
            print(err)
            return
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return ch

    def render(self):
        ANSI.clear_screen()
        ANSI.move_cursor(0, 0)
        self.rows, self.columns = self.size()
        self.buffer.render(self.rows, self.columns)
        ANSI.move_cursor(self.cursor.row, self.cursor.column)

    def handle_input(self):
        character = self.getchar()
        print(character)
        if character == ANSI.CTRL_Q:
            ANSI.clear_screen()
            sys.exit(0)
        elif character == ANSI.ESCAPE:
            character = self.getchar() + self.getchar()
            if character == ANSI.KEY_UP:
                print("UP!!")
                self.cursor, self.buffer = self.cursor.up(self.buffer, self.rows, self.columns)
                return
            if character == ANSI.KEY_DOWN:
                print("DOWN!!")
                self.cursor, self.buffer = self.cursor.down(self.buffer, self.rows, self.columns)
                return
            if character == ANSI.KEY_LEFT:
                print("LEFT!!")
                self.cursor, self.buffer = self.cursor.left(self.buffer, self.rows, self.columns)
                return
            if character == ANSI.KEY_RIGHT:
                print("RIGHT!!")
                self.cursor, self.buffer = self.cursor.right(self.buffer, self.rows, self.columns)
                return
        else:
            self.buffer = self.buffer.insert(
                character, self.cursor.row, self.cursor.column
            )
            self.cursor, self.buffer = self.cursor.right(self.buffer, self.rows, self.columns)


class Buffer(object):
    def __init__(self, lines, display_row=0, display_column=0):
        super(Buffer, self).__init__()
        self.lines = lines
        self.pointer_row = min(max(display_row, 0), self.line_count())
        self.pointer_column = display_column

    def insert(self, char, row, column):
        row = row + self.pointer_row
        if row >= self.line_count():
            return self
        column = column + self.pointer_column
        lines = [line for line in self.lines]

        line = list(lines[row])
        line.insert(column, char)
        lines[row] = "".join(line)
        return Buffer(
            lines,
            display_row=self.pointer_row,
            display_column=self.pointer_column
        )

    def render(self, rows, columns):
        row = self.pointer_row
        col = self.pointer_column
        print("Pointer at %d" % self.pointer_row)
        for line in self.lines[row:row+rows-1]:
            text = line[col:col+columns-1]
            sys.stdout.write(text + ANSI.newline)

    def line_count(self):
        return len(self.lines)

    def line_length(self, row):
        return len(self.lines[row])

    def up(self, count=1):
        return Buffer(
            self.lines,
            display_row=self.pointer_row - count,
            display_column=self.pointer_column,
        )

    def down(self, count=1):
        return Buffer(
            self.lines,
            display_row=self.pointer_row + count,
            display_column=self.pointer_column,
        )

    def left(self, count=1):
        return Buffer(
            self.lines,
            display_row=self.pointer_row,
            display_column=self.pointer_column - count
        )

    def right(self, count=1):
        return Buffer(
            self.lines,
            display_row=self.pointer_row,
            display_column=self.pointer_column + count
        )


class Cursor(object):
    def __init__(self, row=0, column=0):
        super(Cursor, self).__init__()
        self.row = row
        self.column = column

    def clamp(self, buffer, display_rows, display_columns):
        # - # - # - # - # - # - # - # - # - # - # - # - # - # - # - # - # - # -
        #                                 Row                                 #
        # - # - # - # - # - # - # - # - # - # - # - # - # - # - # - # - # - # -
        DEBUG.write("--------------------------------------------------------")
        # DEBUG.write("Clamping.")
        # DEBUG.write("Terminal Size: %d x %d" % (display_rows, display_columns))
        # DEBUG.write("Cursor position: %d x %d" % (self.row, self.column))
        # DEBUG.write("Line count: %d" % (buffer.line_count() - 1))

        # If the row is greater than the line count, clamp.
        cursor_row = min(self.row, buffer.line_count() - 1)
        # If the row is less than 0, clamp.
        # cursor_row = max(cursor_row, 0)

        DEBUG.write("Cursor Row: %d" % cursor_row)
        DEBUG.write("Buffer Row: %d" % buffer.pointer_row)

        DEBUG.write("Screen row: %d" % cursor_row)
        DEBUG.write("Screen down: %s" % (cursor_row >= (display_rows-1)))

        # If the row is greater than the display rows plus display offset,
        # move the display.
        if cursor_row > (display_rows-1):
            offset = cursor_row - (display_rows-1)
            DEBUG.write("Down offset is %d" % offset)
            result_row = offset + cursor_row + buffer.pointer_row - 1
            if result_row > buffer.line_count():
                offset = 0
            buffer = buffer.down(count=offset)
            cursor_row = display_rows - 1
        elif cursor_row < 0:
            offset = cursor_row * -1
            DEBUG.write("Amount above screen: %d" % offset)
            # result_row = cursor_row +
            buffer = buffer.up(count=offset)
            cursor_row = 0
        # If the row is less than the display offset, move the display
        # elif cursor_row < buffer.pointer_row:
        #     offset = buffer.pointer_row - cursor_row
        #     DEBUG.write("Amount above screen: %d" % offset)
        #     buffer = buffer.up(count=offset)

        DEBUG.write(
            "---------\nDisplaying rows %d to %d" % (
                buffer.pointer_row, buffer.pointer_row + display_rows -1
            )
        )
        cursor_row = min(cursor_row, buffer.line_count() - 1)
        cursor_row = max(cursor_row, 0)

        # - # - # - # - # - # - # - # - # - # - # - # - # - # - # - # - # - # -
        #                                Column                               #
        # - # - # - # - # - # - # - # - # - # - # - # - # - # - # - # - # - # -

        # If the column is greater than the line length, clamp.
        cursor_column = min(self.column, buffer.line_length(cursor_row) + 1)
        # If the column is less than 0, clamp.
        cursor_column = max(cursor_column, 0)

        # If the column is greater than the display columns plus display offset
        # Move the display.
        if cursor_column > (buffer.pointer_column + display_columns):
            offset = (buffer.pointer_column + display_columns) - cursor_column
            buffer = buffer.right(count=offset)
        elif cursor_column < buffer.pointer_column:
            offset = buffer.pointer_column - cursor_column
            buffer = buffer.left(count=offset)

        self.row = cursor_row
        self.column = cursor_column
        return self, buffer

    def up(self, buffer, rows, columns, count=1):
        curs = Cursor(self.row - count, self.column)
        return curs.clamp(buffer, rows, columns)

    def down(self, buffer, rows, columns, count=1):
        curs = Cursor(self.row + count, self.column)
        return curs.clamp(buffer, rows, columns)

    def left(self, buffer, rows, columns, count=1):
        curs = Cursor(self.row, self.column - count)
        return curs.clamp(buffer, rows, columns)

    def right(self, buffer, rows, columns, count=1):
        curs = Cursor(self.row, self.column + count)
        return curs.clamp(buffer, rows, columns)


e = Editor()


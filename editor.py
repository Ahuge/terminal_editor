import fcntl
import os
import tty
import termios
import struct
import sys
import traceback


DEBUGGING = True


class DebugFile(object):
    def __init__(self):
        super(DebugFile, self).__init__()
        self.fp = os.path.join(os.path.dirname(__file__), "debug.log")

    def write(self, msg):
        if DEBUGGING:
            with open(self.fp, "a") as fh:
                fh.writelines([msg + "\n"])


DEBUG = DebugFile()


class Ordinal(object):
    ESCAPE = 27
    O = 79
    F = 70
    H = 72
    THREE = 51
    TILDE = 126
    DEL = 127
    CTRL_Q = 17
    LEFT_SQUARE_BRACKET = 91
    UP = 65
    DOWN = 66
    RIGHT = 67
    LEFT = 68


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
            self.lines = list(map(self.strip_line_ending, fh.readlines()))

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
        character = ord(self.getchar())
        DEBUG.write(str(character))

        if character == Ordinal.CTRL_Q:
            ANSI.clear_screen()
            sys.exit(0)
        elif character == Ordinal.DEL:
            original_buffer = self.buffer
            self.buffer = self.buffer.remove(
                self.cursor.row, self.cursor.column-1
            )
            if self.buffer is not original_buffer:
                self.cursor, self.buffer = self.cursor.left(
                    self.buffer,
                    self.rows,
                    self.columns
                )
        elif character == Ordinal.ESCAPE:
            character = ord(self.getchar())
            DEBUG.write(str(character))
            # character = self.getchar() + self.getchar()
            if character == Ordinal.LEFT_SQUARE_BRACKET:
                character = ord(self.getchar())
                DEBUG.write(str(character))
                if character == Ordinal.UP:
                    self.cursor, self.buffer = self.cursor.up(
                        self.buffer,
                        self.rows,
                        self.columns
                    )
                    return
                elif character == Ordinal.DOWN:
                    self.cursor, self.buffer = self.cursor.down(
                        self.buffer,
                        self.rows,
                        self.columns
                    )
                    return
                elif character == Ordinal.LEFT:
                    self.cursor, self.buffer = self.cursor.left(
                        self.buffer,
                        self.rows,
                        self.columns
                    )
                    return
                elif character == Ordinal.RIGHT:
                    self.cursor, self.buffer = self.cursor.right(
                        self.buffer,
                        self.rows,
                        self.columns
                    )
                    return
                elif character == Ordinal.THREE:
                    character = ord(self.getchar())
                    DEBUG.write(str(character))
                    if character == Ordinal.TILDE:
                         # Run a backspace.
                        original_buffer = self.buffer
                        self.buffer = self.buffer.remove(
                            self.cursor.row, self.cursor.column
                        )
                        # if self.buffer is not original_buffer:
                        #     self.cursor, self.buffer = self.cursor.left(
                        #         self.buffer,
                        #         self.rows,
                        #         self.columns,
                        #     )
            elif character == Ordinal.O:
                character = ord(self.getchar())
                DEBUG.write(str(character))
                if character == Ordinal.F:
                    # END key
                    line_length = self.buffer.line_length(
                        self.cursor.row + self.buffer.pointer_row
                    )

                    self.cursor, self.buffer = self.cursor.right(
                        self.buffer,
                        self.rows,
                        self.columns,
                        count=line_length-self.cursor.column
                    )
                elif character == Ordinal.H:
                    # HOME key
                    self.cursor, self.buffer = self.cursor.left(
                        self.buffer,
                        self.rows,
                        self.columns,
                        count=self.cursor.column+self.buffer.pointer_column
                    )


        else:
            original_buffer = self.buffer
            self.buffer = self.buffer.insert(
                chr(character), self.cursor.row, self.cursor.column
            )
            # Only move the cursor if we added something.
            if self.buffer is not original_buffer:
                self.cursor, self.buffer = self.cursor.right(
                    self.buffer,
                    self.rows,
                    self.columns
                )


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

    def remove(self, row, column):
        row = row + self.pointer_row
        if row >= self.line_count():
            return self
        column = column + self.pointer_column
        lines = [line for line in self.lines]

        line = list(lines[row])
        line.pop(column)
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
            if r"\x1b" in text:
                DEBUG.write("ANSI.ESCAPE found!")
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
       # If the row is greater than the line count, clamp.
        cursor_row = min(self.row, buffer.line_count() - 1)

        # If the row is greater than the display rows plus display offset,
        # move the display.
        if cursor_row > (display_rows-1):
            offset = cursor_row - (display_rows-1)
            result_row = offset + cursor_row + buffer.pointer_row - 1
            if result_row > buffer.line_count():
                offset = 0
            buffer = buffer.down(count=offset)
            cursor_row = display_rows - 1
        elif cursor_row < 0:
            offset = cursor_row * -1
            # result_row = cursor_row +
            buffer = buffer.up(count=offset)
            cursor_row = 0

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


import tty
import termios
import sys
import traceback


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

    def getchar(self):
        # Returns a single character from standard input
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(sys.stdin.fileno())
            ch = sys.stdin.read(1)
        except Exception as err:
            print(err)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return ch

    def render(self):
        ANSI.clear_screen()
        ANSI.move_cursor(0, 0)
        self.buffer.render()
        ANSI.move_cursor(self.cursor.row, self.cursor.column)
        pass

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
                self.cursor = self.cursor.up(self.buffer)
                return
            if character == ANSI.KEY_DOWN:
                print("DOWN!!")
                self.cursor = self.cursor.down(self.buffer)
                return
            if character == ANSI.KEY_LEFT:
                print("LEFT!!")
                self.cursor = self.cursor.left(self.buffer)
                return
            if character == ANSI.KEY_RIGHT:
                print("RIGHT!!")
                self.cursor = self.cursor.right(self.buffer)
                return
        self.buffer = self.buffer.insert(
            character, self.cursor.row, self.cursor.column
        )


class Buffer(object):
    def __init__(self, lines):
        super(Buffer, self).__init__()
        self.lines = lines

    def insert(self, char, row, column):
        lines = [line for line in self.lines]

        line = list(lines[row])
        line.insert(column, char)
        lines[row] = "".join(line)
        return Buffer(lines)

    def render(self):
        for line in self.lines:
            sys.stdout.write(line + ANSI.newline)

    def line_count(self):
        return len(self.lines)

    def line_length(self, row):
        return len(self.lines[row])


class Cursor(object):
    def __init__(self, row=0, column=0, buffer=None):
        super(Cursor, self).__init__()
        self.row = row
        self.column = column

    def clamp(self, buffer):
        self.row = min(
            max(self.row, 0),
            buffer.line_count() - 1
        )
        self.column = min(
            max(self.column, 0),
            buffer.line_length(self.row) + 1
        )
        return self

    def up(self, buffer, count=1):
        curs = Cursor(self.row - count, 0, self.column)
        return curs.clamp(buffer)

    def down(self, buffer, count=1):
        curs = Cursor(self.row + count, self.column)
        return curs.clamp(buffer)

    def left(self, buffer, count=1):
        curs = Cursor(self.row, self.column - count, 0)
        return curs.clamp(buffer)

    def right(self, buffer, count=1):
        curs = Cursor(self.row, self.column + count)
        return curs.clamp(buffer)


e = Editor()

class SolutionFound(Exception):
    pass

class NoCandidates(Exception):
    pass

class Game(object):
    def __init__(self):
        self.squares = [Square(position) for position in range(81)]

    def row(self, value):
        squares = [square for square in self.squares if square.row == value]
        return squares

    def rows(self):
        for row in range(9):
            yield self.row(row)

    def column(self, value):
        squares = [square for square in self.squares if square.column == value]
        return squares

    def columns(self):
        for column in range(9):
            yield self.column(column)

    def block(self, value):
        squares = [square for square in self.squares if square.block == value]
        return squares

    def blocks(self):
        for block in range(9):
            yield self.block(block)

    def print_state(self):
        for row in range(9):
            print ' '.join(str(square) for square in self.row(row))

    def assign(self, square, value):
        self.squares[square].assign(value)

    def solved(self):
        states = [square.solved for square in self.squares]
        return states.count(False) == 0

class Square(object):
    def __init__(self, value):
        self.value = value
        self.candidates = set(range(1,10))

    def __str__(self):
        if len(self.candidates) > 1:
            value = '.'
        elif len(self.candidates) == 1:
            value = str(self.solution)
        else:
            value = '!'
        return value

    @property
    def solved(self):
        return len(self.candidates)==1

    @property
    def solution(self):
        if len(self.candidates) == 1:
            solution = list(self.candidates)[0]
        else:
            solution = None
        return solution

    @property
    def column(self):
        return self.value % 9

    @property
    def row(self):
        return self.value // 9

    @property
    def block(self):
        return 3 * (self.row // 3) + self.column // 3

    def eliminate(self, value):
        try:
            self.candidates.remove(value)
        except KeyError:
            pass
        if not self.candidates:
            raise NoCandidates("Square %r has no remaining candidates" % (
                self.value))

    def assign(self, value):
        if not type(value) == int or value < 1 or value > 9:
            raise ValueError("Value %r out of range" % value)
        self.candidates = set([value])

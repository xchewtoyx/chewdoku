class SolutionFound(Exception):
    pass

class InvalidState(Exception):
    pass

class Game(object):
    def __init__(self, app):
        self.app = app
        self.squares = [Square(position) for position in range(81)]

    def row(self, value):
        squares = [square for square in self.squares if square.row == value]
        return Group(squares)

    def rows(self):
        for row in range(9):
            yield self.row(row)

    def column(self, value):
        squares = [square for square in self.squares if square.column == value]
        return Group(squares)

    def columns(self):
        for column in range(9):
            yield self.column(column)

    def block(self, value):
        squares = [square for square in self.squares if square.block == value]
        return Group(squares)

    def blocks(self):
        for block in range(9):
            yield self.block(block)

    def groups(self):
        for row in self.rows():
            yield row
        for column in self.columns():
            yield column
        for block in self.blocks():
            yield block

    def square_groups(self, square):
        return [
            self.row(square.row),
            self.column(square.column),
            self.block(square.block),
        ]

    def common_groups(self, squares):
        for group in self.groups:
            if set(group) > squares:
                yield group

    def print_state(self):
        for row in range(9):
            print ' '.join(str(square) for square in sorted(self.row(row)))

    def candidate_column(self, row, subrow, column):
        column_text = ''
        square = self.squares[row*9 + column]
        for subcolumn in range(3):
            candidate = subrow*3 + subcolumn + 1
            if square.solved:
                column_text += '%d ' % square.solution
            elif candidate in square.candidates:
                column_text += '%d ' % candidate
            else:
                column_text += '  '
        return column_text

    def candidate_subrows(self, row):
        for subrow in range(3):
            subrow_text = ''
            for column in range(9):
                subrow_text += self.candidate_column(
                    row, subrow, column) + '  '
            yield subrow_text

    def print_candidates(self):
        for row in range(9):
            for subrow in self.candidate_subrows(row):
                print subrow
            print

    def assign(self, square, value):
        self.squares[square].assign(value)

    def solved(self):
        states = [square.solved for square in self.squares]
        return False not in states

    def validate(self):
        self.app.log.debug('Validating game state')
        valid_solutions = set(range(1,10))
        for group in self.groups():
            solved_values = [square.solution for square in group.solved]
            self.app.log.debug('group solutions: %r' % solved_values)
            for value in solved_values:
                if value not in valid_solutions:
                    raise InvalidState('Invalid value %r in group %r' % (
                                       value, group))
                if solved_values.count(value) > 1:
                    raise InvalidState('Conflict for value %d in group  %r' % (
                        value, group))

class Group(set):
    @property
    def solved(self):
        solved_squares = [square for square in self if square.solved]
        return set(solved_squares)

    @property
    def unsolved(self):
        return self - self.solved

    @property
    def rows(self):
        return set(square.row for square in self)

    @property
    def columns(self):
        return set(square.column for square in self)

    @property
    def blocks(self):
        return set(square.block for square in self)

    def with_candidate(self, value):
        return Group(square for square in self if value in square.candidates)

class Square(object):
    def __init__(self, value):
        self.value = value
        self.candidates = set(range(1,10))

    def __repr__(self):
        return 'Square<%d (%d, %d)>' % (self.value, self.column, self.row)

    def __str__(self):
        if len(self.candidates) > 1:
            value = '.'
        elif len(self.candidates) == 1:
            value = str(self.solution)
        else:
            value = '!'
        return value

    def __int__(self):
        return self.value

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
        self.candidates.discard(value)
        if not self.candidates:
            raise InvalidState("Square %r has no remaining candidates" % (
                self.value))

    def assign(self, value):
        if not type(value) == int or value < 1 or value > 9:
            raise ValueError("Value %r out of range" % value)
        self.candidates = set([value])

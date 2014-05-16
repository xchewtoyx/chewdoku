from itertools import combinations

from cement.core import controller, handler

from chewdoku.models import Game, SolutionFound, NoCandidates

class Solver(controller.CementBaseController):
    class Meta:
        label='base'
        arguments = [
            (['--input', '-i'], {
                'action': 'store',
                'help': 'File to read puzzle data from',
            }),
            (['--difficulty', '-d'], {
                'action': 'store',
                'type': int,
                'default': 0,
                'help': 'Use techniques up to certain difficulty level.',
            }),
        ]

    def load_puzzle(self):
        initial_state = ''
        with open(self.app.pargs.input, 'r') as input:
            initial_state = input.readline()
        game = Game()
        for square, value in enumerate(initial_state):
            if value.isdigit() and int(value) > 0:
                self.app.log.info('Setting square %r with initial value %r' % (
                    square, value))
                game.assign(square, int(value))
        return game

    def eliminate_from_group(self, group, value, changes):
        for alternate in group:
            if value in alternate.candidates:
                self.app.log.info('Removing %r from square %r' % (
                    value, alternate.value))
                alternate.eliminate(value)
                if alternate.solved:
                    self.app.log.info('%r only value possible for square %r' % (
                        alternate.solution, alternate.value))
                changes.add(True)

    def eliminate_solved(self, game):
        changes = set()
        for square in game.squares:
            if square.solved:
                group = [s for s in game.row(square.row)
                         if square.value != s.value]
                self.eliminate_from_group(group, square.solution, changes)
                group = [s for s in game.column(square.column)
                         if square.value != s.value]
                self.eliminate_from_group(group, square.solution, changes)
                group = [s for s in game.block(square.block)
                         if square.value != s.value]
                self.eliminate_from_group(group, square.solution, changes)
        return True in changes

    def find_single_in_group(self, group, changes):
        unsolved = [square for square in group if not square.solved]
        candidates = set()
        for square in unsolved:
            candidates.update(square.candidates)
        for candidate in candidates:
            squares = [
                square for square in group if candidate in square.candidates]
            if len(squares) == 1:
                square = squares[0]
                self.app.log.info(
                    'Square %r is only candidate in group for %r' % (
                        square.value, candidate))
                square.assign(candidate)
                changes.add(True)

    def find_singles(self, game):
        changes = set()
        for row in game.rows():
            self.find_single_in_group(row, changes)
        for column in game.columns():
            self.find_single_in_group(column, changes)
        for block in game.blocks():
            self.find_single_in_group(block, changes)
        return True in changes

    def find_pair_in_group(self, group, changes):
        unsolved = [square for square in group if not square.solved]
        candidates = set()
        for square in unsolved:
            candidates.update(square.candidates)
        for pair in combinations(candidates, 2):
            squares = [
                square for square in group if set(pair) & square.candidates]
            if len(squares) == 2:
                self.app.log.info(
                    'Found pair %r in squares %r[%r], %r[%r]' % (
                        pair, squares[0].value, squares[0].candidates,
                        squares[1].value, squares[1].candidates
                    ))
                for square in squares:
                    square.candidates = square.candidates & set(pair)
                changes.add(True)

    def find_pairs(self, game):
        changes = set()
        for row in game.rows():
            self.find_pair_in_group(row, changes)
        for column in game.columns():
            self.find_pair_in_group(column, changes)
        for block in game.blocks():
            self.find_pair_in_group(block, changes)
        return True in changes

    def run_solver(self, game):
        while True:
            if self.eliminate_solved(game):
                continue
            if self.find_singles(game):
                continue
            if self.find_pairs(game):
                continue
            break

    @controller.expose(
        aliases=['help'], aliases_only=True, help='Display this message')
    def default(self):
        self.app.args.print_help()

    @controller.expose(help='Display the loaded puzzle')
    def show(self):
        game = self.load_puzzle()
        game.print_state()

    @controller.expose(help='Attempt to solve the puzzle')
    def solve(self):
        game = self.load_puzzle()
        try:
            self.run_solver(game)
        except (SolutionFound, NoCandidates) as exception:
            self.app.log.info('Terminating solution: %r' % exception)
        game.print_state()

def load():
    handler.register(Solver)

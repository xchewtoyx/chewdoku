from itertools import combinations

from cement.core import controller, handler

from chewdoku.models import Game, SolutionFound, InvalidState

class Solver(controller.CementBaseController):
    class Meta:
        label='base'
        arguments = [
            (['--input', '-i'], {
                'action': 'store',
                'help': 'File to read puzzle data from',
            }),
            (['--line', '-l'], {
                'action': 'store',
                'default': 1,
                'type': int,
                'help': 'Line number to read from file',
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
            for line in range(self.app.pargs.line):
                initial_state = input.readline()
        game = Game(self.app)
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
                    'Square %d is only candidate in group for %r' % (
                        square, candidate))
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

    def naked_subset(self, game, group, subset, changes):
        squares = set()
        for square in group:
            if subset == square.candidates:
                squares.add(square)
        if len(squares) == len(subset):
            conflicts = set()
            for square in group:
                if square.candidates & subset and not square in squares:
                    conflicts.add(square)
            if conflicts:
                self.app.log.debug(
                    'Found naked subset %r in squares %r' % (
                        subset, [square.value for square in squares]))
                for value in subset:
                    self.eliminate_from_group(conflicts, value, changes)

    def find_pair_in_group(self, game, group, changes):
        unsolved = [square for square in group if not square.solved]
        candidates = set()
        for square in unsolved:
            candidates.update(square.candidates)
        for pair in combinations(candidates, 2):
            pair = set(pair)
            squares = []
            self.naked_subset(game, unsolved, pair, changes)

    def find_pairs(self, game):
        changes = set()
        for group in game.groups():
            self.find_pair_in_group(game, group, changes)
        return True in changes

    def find_candidate_lines(self, game):
        changes = set()
        for group in game.groups():
            unsolved = set([square for square in group if not square.solved])
            values = set()
            for square in unsolved:
                values.union(square.candidates)
            for value in values:
                positions = [square for square in unsolved]
                eliminated = set.union(game.common_groups(positions)) - group
                if eliminated:
                    self.app.log.info('Block-line interaction.'
                                      '%d in [%r] eliminates [%r]' % (
                                          value, positions, eliminated))
                    self.eliminate_from_group(group, value, changes)
                    changes.add(True)
        return changes

    def run_solver(self, game):
        levels = set()
        while True:
            self.app.log.debug('Validating game state')
            game.validate()
            self.app.log.debug('Eliminating values based on solved cells')
            if self.eliminate_solved(game):
                levels.add(1)
                continue
            self.app.log.debug('Searching for unique candidates')
            if self.find_singles(game):
                levels.add(2)
                continue
            self.app.log.debug('Eliminating based on candidate lines')
            if self.find_candidate_lines(game):
                levels.add(3)
                continue
            self.app.log.debug('Searching for pairs')
            if self.find_pairs(game):
                levels.add(4)
                continue
            game.validate()
            break
        self.app.log.info('Puzzle difficulty level: %d' % max(levels))
        self.app.log.info('levels used: %r' % sorted(levels))

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
        except (SolutionFound, InvalidState, ValueError) as exception:
            self.app.log.info('Terminating solution: %r' % exception)
        game.print_state()

def load():
    handler.register(Solver)

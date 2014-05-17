from itertools import combinations

from cement.core import controller, handler

from chewdoku.models import Game, Group, SolutionFound, InvalidState

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
            (['--progress', '-v'], {
                'action': 'store_true',
                'help': 'Print candidate table before each solve pass.'
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
                    value, alternate))
                alternate.eliminate(value)
                if alternate.solved:
                    self.app.log.info('%r only value possible for square %r' % (
                        alternate.solution, alternate))
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
        squares = Group()
        for square in group:
            if subset >= square.candidates:
                squares.add(square)
        if len(squares) == len(subset):
            conflicts = Group()
            for value in subset:
                conflicts |= group.with_candidate(value)
            conflicts = conflicts - squares
            if conflicts:
                self.app.log.debug(
                    'Found naked subset %r in squares %r' % (
                        subset, squares))
                for value in subset:
                    self.eliminate_from_group(conflicts, value, changes)

    def hidden_subset(self, game, group, subset, changes):
        squares = Group()
        for square in group:
            if subset & square.candidates:
                squares.add(square)
        if len(squares) == len(subset):
            candidates = set()
            for square in squares:
                candidates |= square.candidates
            candidates -= subset
            if candidates:
                self.app.log.debug(
                    'Found hidden subset %r in squares %r' % (
                        subset, squares))
                for value in candidates:
                    self.eliminate_from_group(squares, value, changes)

    def find_subset_in_group(self, game, group, size, changes):
        unsolved = group.unsolved
        candidates = set()
        for square in unsolved:
            candidates.update(square.candidates)
        for subset in combinations(candidates, size):
            subset = set(subset)
            self.naked_subset(game, unsolved, subset, changes)
            self.hidden_subset(game, unsolved, subset, changes)

    def find_pairs(self, game):
        changes = set()
        for group in game.groups():
            self.find_subset_in_group(game, group, 2, changes)
        return True in changes

    def find_triplets(self, game):
        changes = set()
        for group in game.groups():
            self.find_subset_in_group(game, group, 3, changes)
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

    def find_hidden_lines(self, game):
        block_pairs = combinations(game.blocks(), 2)
        changes = set()
        for pair in block_pairs:
            squares = pair[0] | pair[1]
            unsolved = squares.unsolved
            values = set()
            for square in unsolved:
                values |= square.candidates
            for value in values:
                potential_squares = squares.with_candidate(value)
                eliminated = Group()
                # If pair of horizontal blocks
                if ( pair[0].rows == pair[1].rows and
                     len(potential_squares.rows) == 2 ):
                    for row in potential_squares.rows:
                        eliminated |= game.row(row)
                if ( pair[0].columns == pair[1].columns and
                     len(potential_squares.columns) == 2 ):
                    for column in potential_squares.columns:
                        eliminated |= game.column(column)
                eliminated -= squares
                eliminated = eliminated.with_candidate(value)
                if eliminated:
                    self.app.log.info(
                        'Block block interaction for value %d. '
                        'Eliminating from %r due to %r.' % (
                            value, eliminated, potential_squares))
                    self.eliminate_from_group(eliminated, value, changes)
            if True in changes:
                return True
        return False

    def run_solver(self, game):
        levels = set([0])
        while True:
            if self.app.pargs.progress:
                game.print_candidates()
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
            self.app.log.debug('Eliminating based on hidden lines')
            if self.find_hidden_lines(game):
                levels.add(4)
                continue
            self.app.log.debug('Searching for pairs')
            if self.find_pairs(game):
                levels.add(5)
                continue
            self.app.log.debug('Searching for triplets')
            if self.find_triplets(game):
                levels.add(6)
                continue
            game.validate()
            break
        level = str(max(levels))
        if game.solved():
            self.app.log.info('Puzzle solved.')
        else:
            level = '*'
        self.app.log.info('Puzzle difficulty level: ' + level)
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

    @controller.expose(help='Show candidate status at end of solve attempt')
    def candidates(self):
        game = self.load_puzzle()
        self.eliminate_solved(game)
        game.print_candidates()

def load():
    handler.register(Solver)

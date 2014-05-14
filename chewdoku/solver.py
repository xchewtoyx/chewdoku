from cement.core import controller, handler

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

    @controller.expose(
        aliases=['help'], aliases_only=True, help='Display this message')
    def default(self):
        self.app.args.print_help()

    @controller.expose(help='Display the loaded puzzle')
    def show(self):
        pass

def load():
    handler.register(Solver)

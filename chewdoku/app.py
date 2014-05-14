from cement.core import foundation, controller, handler
from chewdoku import solver

def run():
    app = foundation.CementApp(label='chewdoku')
    solver.load()
    try:
        app.setup()
        app.run()
    finally:
        app.close

if __name__ == '__main__':
    run()

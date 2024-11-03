import multiprocessing

from waitress import serve

from ChromeController.ProcessManager import Manager
from repricerDjango import wsgi

if __name__ == "__main__":
    queue = multiprocessing.Queue()
    manager = Manager(7)
    manager.start()
    serve(wsgi.application, host='127.0.0.1', port=8000, connection_limit=300)


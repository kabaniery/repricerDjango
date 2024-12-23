from waitress import serve

from ChromeController.ProcessManager import Manager
from manager_queue import get_queue, set_queue
from repricerDjango import wsgi
import multiprocessing

if __name__ == "__main__":
    man = multiprocessing.Manager()
    set_queue(man.Queue())
    manager = Manager(5, get_queue())
    if not manager.started:
        manager.start()
    serve(wsgi.application, host='127.0.0.1', port=8000)


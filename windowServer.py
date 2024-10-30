import os

import django
from waitress import serve


from manager_queue import get_queue, set_queue
import multiprocessing

if __name__ == "__main__":
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'repricerDjango.settings')
    django.setup()
    from ChromeController.ProcessManager import Manager
    from repricerDjango import wsgi
    man = multiprocessing.Manager()
    set_queue(man.Queue())
    manager = Manager(3, get_queue())
    if not manager.started:
        manager.start()
    serve(wsgi.application, host='127.0.0.1', port=8000, connection_limit=300)


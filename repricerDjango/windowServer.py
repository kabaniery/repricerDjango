import time

from waitress import serve

from repricer.ChromeProcess.ChromeController import ChromeController
from repricerDjango import wsgi

if __name__ == "__main__":
    ChromeController.main_activity = ChromeController()
    ChromeController.main_activity.start()
    serve(wsgi.application, host='127.0.0.1', port=8000)


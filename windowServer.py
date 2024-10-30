from waitress import serve

from repricerDjango import wsgi

if __name__ == "__main__":
    # Manager(3).start()
    serve(wsgi.application, host='127.0.0.1', port=8000, connection_limit=300)


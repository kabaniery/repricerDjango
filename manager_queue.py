from multiprocessing import Manager

queue = None


def get_queue():
    global queue
    return queue


def set_queue(q):
    global queue
    queue = q

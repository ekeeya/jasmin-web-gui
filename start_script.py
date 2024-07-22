import threading
from twisted.internet import reactor


def start_reactor():
    reactor.run(installSignalHandlers=0)


reactor_thread = threading.Thread(target=start_reactor)
reactor_thread.start()

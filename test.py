import pickle as pickle
from twisted.internet import reactor, defer
from jasmin.managers.proxies import SMPPClientManagerPBProxy
from jasmin.routing.proxies import RouterPBProxy
from jasmin.routing.Routes import DefaultRoute
from jasmin.routing.jasminApi import User, Group
from twisted.internet.threads import blockingCallFromThread


@defer.inlineCallbacks
def runScenario():
    proxy_router = RouterPBProxy()
    try:
        # Connect to Router PB proxy
        print("Attempting to connect to Jasmin router pb...")
        yield proxy_router.connect('127.0.0.1', 8988, 'radmin', 'rpwd')
        print('Connected to Radmin')
        g1 = Group("xxxxxxx")
        g = yield proxy_router.group_add(g1)
        return g
    except Exception as e:
        print("ERROR RUNNING SCENARIO: %s" % str(e))


def run():
    d = runScenario()
    d.addCallback(print_result)
    d.addErrback(print_error)


def print_result(result):
    print(f"Result of async_add: {result}")


def print_error(error):
    print(f"Error occurred: {error}")


def execute():
    blockingCallFromThread(reactor, run)

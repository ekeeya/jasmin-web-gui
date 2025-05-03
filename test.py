"""
An example of scenario with the following actions:
 1. Add and start a SMPP Client connector
 2. Provision a DefaultRoute to that connector
 3. Provision a User

This is a demonstration of using PB (PerspectiveBroker) API to gain control Jasmin.

The jasmin SMS gateway shall be already running and having
a pb listening on 8989 (for SMPP) and 8988 (for Router).
"""

import pickle
from twisted.internet import reactor, defer
from jasmin.managers.proxies import SMPPClientManagerPBProxy
from jasmin.routing.proxies import RouterPBProxy
from jasmin.routing.Routes import DefaultRoute
from jasmin.routing.jasminApi import User, Group, Connector, SmppClientConnector
from jasmin.protocols.smpp.configs import SMPPClientConfig


@defer.inlineCallbacks
def runScenario():
    try:
        # First part, SMPP Client connector management
        ###############################################
        print("Connecting to SMPP Client Manager...")
        proxy_smpp = SMPPClientManagerPBProxy()
        yield proxy_smpp.connect('127.0.0.1', 8989, 'cmadmin', 'cmpwd')

        # Provision SMPPClientManagerPBProxy with a connector and start it
        print("Adding SMPP connector...")
        connector_config = {
            'id': 'abc',
            'username': 'smppclient1',
            'password': 'password',  # Added required field
            'host': '127.0.0.1',  # Added required field
            'port': 2775,  # Added required field
            'reconnectOnConnectionFailure': True
        }
        config1 = SMPPClientConfig(**connector_config)
        yield proxy_smpp.add(config1)

        print("Starting SMPP connector...")
        yield proxy_smpp.start('abc')

        # Second part, User and Routing management
        ###########################################
        print("\nConnecting to Router Manager...")
        proxy_router = RouterPBProxy()
        yield proxy_router.connect('127.0.0.1', 8988, 'radmin', 'rpwd')

        # Provision RouterPBProxy with MT routes
        print("Adding DefaultRoute...")
        yield proxy_router.mtroute_add(DefaultRoute(connector=SmppClientConnector('abc'), rate=20.0), 0)
        yield proxy_router.persist()
        routes = yield proxy_router.mtroute_get_all()
        print("\nConfigured routes:")
        for route in pickle.loads(routes):
            print(f"\t{route}")

        # Provision router with users
        print("\nAdding group and user...")
        g1 = Group(1)
        u1 = User(uid=1, group=g1, username='foo', password='bar')
        yield proxy_router.group_add(g1)
        yield proxy_router.user_add(u1)

        users = yield proxy_router.user_get_all()
        print("\nUsers:")
        for user in pickle.loads(users):
            print(f"\t{user}")

        # Last, tear down
        ##################
        print("\nStopping SMPP connector...")
        yield proxy_smpp.stop('abc')

        print("\nScenario completed successfully!")

    except Exception as e:
        print(f"\nERROR RUNNING SCENARIO: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        reactor.stop()


if __name__ == '__main__':
    print("Starting scenario...")
    runScenario()
    reactor.run()

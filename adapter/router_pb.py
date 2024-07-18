import pickle
from twisted.internet import defer, reactor
from jasmin.routing.proxies import RouterPBProxy
from jasmin.routing.Filters import DestinationAddrFilter
from jasmin.routing.Routes import DefaultRoute, StaticMTRoute
from jasmin.protocols.cli.smppccm import JCliSMPPClientConfig as SmppClientConnector
from jasmin.routing.jasminApi import User, Group
from quark.utils import logger
from django.conf import settings
from jasmin.tools.proxies import ConnectedPB


class RouterPBInterface(RouterPBProxy):
    host = settings.JASMIN_ROUTER_PB_HOST
    port = settings.JASMIN_ROUTER_PB_PORT
    username = settings.JASMIN_ROUTER_PB_USERNAME
    password = settings.JASMIN_ROUTER_PB_PASSWORD

    def __init__(self):
        super().__init__()

    @defer.inlineCallbacks
    def connect(self):
        try:
            yield super().connect(self.host, self.port, self.username, self.password)
        except Exception as e:
            logger.error(f"Error connecting to Jasmin PB: {e}")

    @defer.inlineCallbacks
    def add_group(self, group_name: str, persist: bool = True):
        try:
            group = Group(group_name)
            yield self.group_add(group)
            if persist:
                yield self.persist()
        except Exception as e:
            logger.error("Error adding group to Jasmin PB: %s", e)

    @defer.inlineCallbacks
    def add_user(self, username: str, password: str, group: Group, persist: bool = True):
        try:
            user = User(username=username, password=password, group=group, uid=username)
            yield self.user_add(user)
            if persist:
                yield self.persist()
        except Exception as e:
            logger.error("Error adding user to Jasmin PB: %s", e)

    @defer.inlineCallbacks
    def get_all_users(self):
        try:
            users = yield self.user_get_all()
            return pickle.loads(users)
        except Exception as e:
            logger.error("Error getting all users from Jasmin PB: %s", e)

    @defer.inlineCallbacks
    def get_all_groups(self):
        try:
            groups = yield self.group_get_all()
            return pickle.loads(groups)
        except Exception as e:
            logger.error("Error getting all groups from Jasmin PB: %s", e)

    @defer.inlineCallbacks
    def add_mtrouter(self, connector, filter=None, persist=True):
        try:
            if filter:
                destination = DestinationAddrFilter(destination_addr=filter)
                yield self.mtroute_add(StaticMTRoute([destination], SmppClientConnector(connector)), 1000)
            else:
                yield self.mtroute_add(DefaultRoute(SmppClientConnector(connector)), 1000)
            if persist:
                yield self.persist()
        except Exception as e:
            logger.error("Error adding MT router to Jasmin PB: %s", e)

    @defer.inlineCallbacks
    def add_morouter(self, connector, filter=None, persist=True):
        # Placeholder for MO router functionality
        pass

    def close(self):
        if reactor.running:  # only stop if running
            reactor.stop()

    def execute(self, callback):
        reactor.callWhenRunning(callback)
        reactor.run()

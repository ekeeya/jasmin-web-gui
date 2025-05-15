import logging
import pickle

from django.conf import settings
from jasmin.routing.Interceptors import Interceptor
from jasmin.routing.Routes import DefaultRoute, StaticMTRoute, RandomRoundrobinMTRoute, FailoverMTRoute, Route
from jasmin.routing.jasminApi import User, Group
from jasmin.routing.proxies import RouterPBProxy
from twisted.internet import defer, reactor
from twisted.internet.threads import blockingCallFromThread

logger = logging.getLogger(__name__)


class RouterPBInterface(RouterPBProxy):
    host = settings.JASMIN_ROUTER_PB_HOST
    port = settings.JASMIN_ROUTER_PB_PORT
    username = settings.JASMIN_ROUTER_PB_USERNAME
    password = settings.JASMIN_ROUTER_PB_PASSWORD

    def __init__(self):
        self.deferred = None

    def set_deferred(self, deferred):
        self.deferred = deferred

    @defer.inlineCallbacks
    def pb_connect(self):
        logger.debug("Establishing a connection to jasmin")
        yield super().connect(self.host, self.port, self.username, self.password)
        logger.debug("Established a connection to jasmin")

    @defer.inlineCallbacks
    def add_group(self, group_name: str, persist: bool = True):
        try:
            logger.debug("Establishing a connection to jasmin")
            yield self.pb_connect()
            group = Group(group_name)
            yield self.group_add(group)
            logger.debug(f"Added group {group_name}")
            if persist:
                yield self.persist()
        except Exception as e:
            logger.error(e)
            yield self.disconnect()
            raise e  # raise it again such that we pass it on to the caller
        finally:
            logger.debug("Will disconnect from jasmin")
            self.disconnect()

    @defer.inlineCallbacks
    def remove_groups(self, group_name: str = None):
        try:
            yield self.pb_connect()
            if group_name:
                logger.debug(f"Removing group {group_name}")
                yield self.group_remove(group_name)
            else:
                logger.debug(f"Removing all groups")
                yield self.group_remove_all()
        except Exception as e:
            logger.error(e)
            raise e  # raise it again
        finally:
            yield self.persist()
            logger.debug("Will disconnect from jasmin")
            self.disconnect()

    @defer.inlineCallbacks
    def add_user(self, username: str, password: str, group: Group,
                 mt_credentials,
                 smpps_credential,
                 persist: bool = True):
        try:
            yield self.pb_connect()
            user = User(username=username, password=password, group=group, uid=username, mt_credential=mt_credentials,
                        smpps_credential=smpps_credential)
            yield self.user_add(user)
            if persist:
                yield self.persist()
        except Exception as e:
            logger.error("Error adding user to Jasmin PB: %s", e)
        finally:
            self.disconnect()

    @defer.inlineCallbacks
    def remove_user(self, uid: str, persist: bool = True):
        try:
            yield self.pb_connect()
            yield self.user_remove(uid)
            if persist:
                yield self.persist()
        except Exception as e:
            logger.error("Error removing user to Jasmin PB: %s", e)
        finally:
            self.disconnect()

    @defer.inlineCallbacks
    def get_all_users(self):
        try:
            yield self.pb_connect()
            users = yield self.user_get_all()
            return pickle.loads(users)
        except Exception as e:
            logger.error("Error getting all users from Jasmin PB: %s", e)

    @defer.inlineCallbacks
    def get_all_groups(self):
        try:
            yield self.pb_connect()
            groups = yield self.group_get_all()
            return pickle.loads(groups)
        finally:
            self.disconnect()

    @defer.inlineCallbacks
    def add_route(self, route: Route, order, nature, persist=True):
        try:
            yield self.pb_connect()
            if nature == "MT":
                yield self.mtroute_add(route, order)
            else:
                yield self.moroute_add(route, order)
            if persist:
                yield self.persist()
        except Exception as e:
            logger.error("Error adding MT router to Jasmin PB: %s", e)

    @defer.inlineCallbacks
    def remove_route(self, order, nature, persist=True):
        try:
            yield self.pb_connect()
            if nature == "MT":
                yield self.mtroute_remove(order)
            else:
                yield self.moroute_remove(order)
            if persist:
                yield self.persist()
        except Exception as e:
            logger.error("Error removing MT router to Jasmin PB: %s", e)

    @defer.inlineCallbacks
    def add_interceptor(self, interceptor: Interceptor, order, nature, persist=True):
        try:
            yield self.pb_connect()
            if nature == "MT":
                yield self.mtinterceptor_add(interceptor, order)
            else:
                yield self.mointerceptor_add(interceptor, order)
            if persist:
                yield self.persist()
        except Exception as e:
            logger.error("Error adding router from Jasmin PB: %s", e)

    @defer.inlineCallbacks
    def remove_interceptor(self, order, nature, persist=True):
        try:
            yield self.pb_connect()
            if nature == "MT":
                yield self.mtinterceptor_remove(order)
            else:
                yield self.mointerceptor_remove(order)
            if persist:
                yield self.persist()
        except Exception as e:
            logger.error("Error removing interceptor from Jasmin PB: %s", e)

    def execute(self):
        def run():
            d = self.deferred

        # see https://docs.twistedmatrix.com/en/stable/api/twisted.internet.threads.html#blockingCallFromThread
        # # force our deferred to execute sync
        blockingCallFromThread(reactor, run)

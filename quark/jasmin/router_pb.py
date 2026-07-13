import logging
import pickle

from django.conf import settings
from jasmin.routing.Interceptors import Interceptor
from jasmin.routing.Routes import Route
from jasmin.routing.jasminApi import User, Group
from jasmin.routing.proxies import RouterPBProxy
from twisted.internet import defer

logger = logging.getLogger(__name__)


class RouterPBInterface(RouterPBProxy):
    """
    Connection-per-operation wrapper around Jasmin's RouterPBProxy.

    Every method connects, runs the operation, optionally persists, and always
    disconnects. Errors are re-raised (never swallowed) so callers can report
    a truthful outcome. All methods return Deferreds and must be executed in
    the reactor thread via quark.jasmin.reactor.run_in_reactor().
    """

    host = settings.JASMIN_ROUTER_PB_HOST
    port = settings.JASMIN_ROUTER_PB_PORT
    username = settings.JASMIN_ROUTER_PB_USERNAME
    password = settings.JASMIN_ROUTER_PB_PASSWORD

    @defer.inlineCallbacks
    def pb_connect(self):
        logger.debug("Establishing a connection to jasmin RouterPB")
        yield super().connect(self.host, self.port, self.username, self.password)

    @defer.inlineCallbacks
    def add_group(self, group_name: str, persist: bool = True):
        try:
            yield self.pb_connect()
            result = yield self.group_add(Group(group_name))
            logger.debug(f"Added group {group_name}")
            if persist:
                yield self.persist()
            defer.returnValue(result)
        finally:
            self.disconnect()

    @defer.inlineCallbacks
    def remove_groups(self, group_name: str = None, persist: bool = True):
        try:
            yield self.pb_connect()
            if group_name:
                logger.debug(f"Removing group {group_name}")
                result = yield self.group_remove(group_name)
            else:
                logger.debug("Removing all groups")
                result = yield self.group_remove_all()
            if persist:
                yield self.persist()
            defer.returnValue(result)
        finally:
            self.disconnect()

    @defer.inlineCallbacks
    def group_enable(self, gid: str, persist: bool = True):
        try:
            yield self.pb_connect()
            result = yield super().group_enable(gid)
            if persist:
                yield self.persist()
            defer.returnValue(result)
        finally:
            self.disconnect()

    @defer.inlineCallbacks
    def group_disable(self, gid: str, persist: bool = True):
        try:
            yield self.pb_connect()
            result = yield super().group_disable(gid)
            if persist:
                yield self.persist()
            defer.returnValue(result)
        finally:
            self.disconnect()

    @defer.inlineCallbacks
    def add_user(self, username: str, password: str, group: Group,
                 mt_credentials,
                 smpps_credential,
                 persist: bool = True):
        try:
            yield self.pb_connect()
            user = User(username=username, password=password, group=group, uid=username,
                        mt_credential=mt_credentials, smpps_credential=smpps_credential)
            result = yield self.user_add(user)
            if persist:
                yield self.persist()
            defer.returnValue(result)
        finally:
            self.disconnect()

    @defer.inlineCallbacks
    def remove_user(self, uid: str, persist: bool = True):
        try:
            yield self.pb_connect()
            result = yield self.user_remove(uid)
            if persist:
                yield self.persist()
            defer.returnValue(result)
        finally:
            self.disconnect()

    @defer.inlineCallbacks
    def user_enable(self, uid: str, persist: bool = True):
        try:
            yield self.pb_connect()
            result = yield super().user_enable(uid)
            if persist:
                yield self.persist()
            defer.returnValue(result)
        finally:
            self.disconnect()

    @defer.inlineCallbacks
    def user_disable(self, uid: str, persist: bool = True):
        try:
            yield self.pb_connect()
            result = yield super().user_disable(uid)
            if persist:
                yield self.persist()
            defer.returnValue(result)
        finally:
            self.disconnect()

    @defer.inlineCallbacks
    def get_all_users(self, gid: str = None):
        try:
            yield self.pb_connect()
            users = yield self.user_get_all(gid)
            defer.returnValue(pickle.loads(users))
        finally:
            self.disconnect()

    @defer.inlineCallbacks
    def get_user(self, uid: str):
        """Return a single User by uid, or None. Jasmin only exposes user_get_all."""
        try:
            yield self.pb_connect()
            users = pickle.loads((yield self.user_get_all()))
            for user in users or []:
                if getattr(user, "uid", None) == uid or getattr(user, "username", None) == uid:
                    defer.returnValue(user)
            defer.returnValue(None)
        finally:
            self.disconnect()

    @defer.inlineCallbacks
    def get_all_groups(self):
        try:
            yield self.pb_connect()
            groups = yield self.group_get_all()
            defer.returnValue(pickle.loads(groups))
        finally:
            self.disconnect()

    @defer.inlineCallbacks
    def add_route(self, route: Route, order, nature, persist=True):
        try:
            yield self.pb_connect()
            if nature == "MT":
                result = yield self.mtroute_add(route, order)
            else:
                result = yield self.moroute_add(route, order)
            if persist:
                yield self.persist()
            defer.returnValue(result)
        finally:
            self.disconnect()

    @defer.inlineCallbacks
    def remove_route(self, order, nature, persist=True):
        try:
            yield self.pb_connect()
            if nature == "MT":
                result = yield self.mtroute_remove(order)
            else:
                result = yield self.moroute_remove(order)
            if persist:
                yield self.persist()
            defer.returnValue(result)
        finally:
            self.disconnect()

    @defer.inlineCallbacks
    def add_interceptor(self, interceptor: Interceptor, order, nature, persist=True):
        try:
            yield self.pb_connect()
            if nature == "MT":
                result = yield self.mtinterceptor_add(interceptor, order)
            else:
                result = yield self.mointerceptor_add(interceptor, order)
            if persist:
                yield self.persist()
            defer.returnValue(result)
        finally:
            self.disconnect()

    @defer.inlineCallbacks
    def remove_interceptor(self, order, nature, persist=True):
        try:
            yield self.pb_connect()
            if nature == "MT":
                result = yield self.mtinterceptor_remove(order)
            else:
                result = yield self.mointerceptor_remove(order)
            if persist:
                yield self.persist()
            defer.returnValue(result)
        finally:
            self.disconnect()

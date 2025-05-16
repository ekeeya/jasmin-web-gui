#
#  Copyright (c) 2024
#  Created On: 2024/7/18
#  By: Emmanuel Keeya
#  Email: ekeeya@thothcode.tech
#
#  This project is licensed under the GNU General Public License v3.0. You may
#  redistribute it and/or modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This project is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
#  without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#  See the GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License along with this project.
#  If not, see <http://www.gnu.org/licenses/>.
#
import logging
import pickle as pickle

from django.conf import settings
from jasmin.managers.proxies import SMPPClientManagerPBProxy
from jasmin.protocols.cli.smppccm import JCliSMPPClientConfig
from twisted.internet import reactor, defer
from twisted.internet.threads import blockingCallFromThread

logger = logging.getLogger(__name__)


class SmppPBAdapter(SMPPClientManagerPBProxy):
    host = settings.JASMIN_SMPP_PB_HOST
    port = settings.JASMIN_SMPP_PB_PORT
    username = settings.JASMIN_SMPP_PB_USERNAME
    password = settings.JASMIN_SMPP_PB_PASSWORD

    def __init__(self):
        self.deferred = None

    def set_deferred(self, deferred):
        self.deferred = deferred

    @defer.inlineCallbacks
    def pb_connect(self):
        yield super().connect(self.host, self.port, self.username, self.password)

    @defer.inlineCallbacks
    def add_connector(self, smpp_config: JCliSMPPClientConfig, persist: bool = True):
        try:
            logger.debug("Establishing a connection to jasmin")

            yield self.pb_connect()
            yield self.add(smpp_config)
            logger.debug(f"Added SMPP client connector {smpp_config.id}")
            if persist:
                yield self.persist()
        except Exception as e:
            logger.error(e)
            self.disconnect()
            raise e  # raise it again such that we pass it on to the caller
        finally:
            self.disconnect()

    @defer.inlineCallbacks
    def start_connector(self, cid: str):
        yield self.pb_connect()
        yield self.start(cid)

    @defer.inlineCallbacks
    def stop_connector(self, cid: str):
        yield self.pb_connect()
        yield self.stop(cid)

    @defer.inlineCallbacks
    def delete_connector(self, cid: str, persist: bool = True):
        yield self.pb_connect()
        yield self.remove(cid)
        if persist:
            yield self.persist()

    @defer.inlineCallbacks
    def get_connector(self, cid: str):
        yield self.pb_connect()
        connector = yield self.connector_details(cid)
        return pickle.loads(connector)

    @defer.inlineCallbacks
    def connector_status(self, cid: str):
        yield self.pb_connect()
        status = yield self.service_status(cid)
        return True if status == 1 else False

    @defer.inlineCallbacks
    def connector_session(self, cid: str):
        yield self.pb_connect()
        session = yield self.session_state(cid)
        return session

    def execute(self):
        def run():
            d = self.deferred

        # see https://docs.twistedmatrix.com/en/stable/api/twisted.internet.threads.html#blockingCallFromThread
        # # force our deferred to execute sync
        blockingCallFromThread(reactor, run)

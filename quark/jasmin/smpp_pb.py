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
import pickle

from django.conf import settings
from jasmin.managers.proxies import SMPPClientManagerPBProxy
from jasmin.protocols.cli.smppccm import JCliSMPPClientConfig
from twisted.internet import defer

logger = logging.getLogger(__name__)


class SmppPBAdapter(SMPPClientManagerPBProxy):
    """
    Connection-per-operation wrapper around Jasmin's SMPPClientManagerPBProxy.

    Every method connects, runs the operation, optionally persists, and always
    disconnects. Errors are re-raised (never swallowed) so callers can report
    a truthful outcome. All methods return Deferreds and must be executed in
    the reactor thread via quark.jasmin.reactor.run_in_reactor().
    """

    host = settings.JASMIN_SMPP_PB_HOST
    port = settings.JASMIN_SMPP_PB_PORT
    username = settings.JASMIN_SMPP_PB_USERNAME
    password = settings.JASMIN_SMPP_PB_PASSWORD

    @defer.inlineCallbacks
    def pb_connect(self):
        logger.debug("Establishing a connection to jasmin SMPPClientManagerPB")
        yield super().connect(self.host, self.port, self.username, self.password)

    @defer.inlineCallbacks
    def add_connector(self, smpp_config: JCliSMPPClientConfig, persist: bool = True):
        try:
            yield self.pb_connect()
            result = yield self.add(smpp_config)
            logger.debug(f"Added SMPP client connector {smpp_config.id}")
            if persist:
                yield self.persist()
            defer.returnValue(result)
        finally:
            self.disconnect()

    @defer.inlineCallbacks
    def update_connector(self, smpp_config: JCliSMPPClientConfig, persist: bool = True):
        """
        Jasmin's PB has no in-place connector update: remove then re-add.
        Note this stops the connector if it was running; callers should restart it.
        """
        try:
            yield self.pb_connect()
            yield self.remove(smpp_config.id)  # returns False when unknown, that's fine
            result = yield self.add(smpp_config)
            logger.debug(f"Updated SMPP client connector {smpp_config.id}")
            if persist:
                yield self.persist()
            defer.returnValue(result)
        finally:
            self.disconnect()

    @defer.inlineCallbacks
    def start_connector(self, cid: str):
        try:
            yield self.pb_connect()
            result = yield self.start(cid)
            defer.returnValue(result)
        finally:
            self.disconnect()

    @defer.inlineCallbacks
    def stop_connector(self, cid: str):
        try:
            yield self.pb_connect()
            result = yield self.stop(cid)
            defer.returnValue(result)
        finally:
            self.disconnect()

    @defer.inlineCallbacks
    def delete_connector(self, cid: str, persist: bool = True):
        try:
            yield self.pb_connect()
            result = yield self.remove(cid)
            if persist:
                yield self.persist()
            defer.returnValue(result)
        finally:
            self.disconnect()

    @defer.inlineCallbacks
    def get_connector(self, cid: str):
        try:
            yield self.pb_connect()
            connector = yield self.connector_details(cid)
            defer.returnValue(pickle.loads(connector))
        finally:
            self.disconnect()

    @defer.inlineCallbacks
    def connector_status(self, cid: str):
        try:
            yield self.pb_connect()
            status = yield self.service_status(cid)
            defer.returnValue(status == 1)
        finally:
            self.disconnect()

    @defer.inlineCallbacks
    def connector_session(self, cid: str):
        try:
            yield self.pb_connect()
            session = yield self.session_state(cid)
            defer.returnValue(session)
        finally:
            self.disconnect()

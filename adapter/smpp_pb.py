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
from quark.utils import logger
from django.conf import settings
from twisted.internet import reactor, defer
from jasmin.managers.proxies import SMPPClientManagerPBProxy
from jasmin.protocols.smpp.configs import SMPPClientConfig
from jasmin.protocols.cli.smppccm import JCliSMPPClientConfig as SmppClientConnector
import pickle as pickle


class SmppPBAdapter:
    host = settings.JASMIN_SMPP_PB_HOST
    port = settings.JASMIN_SMPP_PB_PORT
    username = settings.JASMIN_SMPP_PB_USERNAME
    password = settings.JASMIN_SMPP_PB_PASSWORD

    def __init__(self):
        self.proxy_smpp = None

    @defer.inlineCallbacks
    def connect(self):
        try:
            self.proxy_smpp = SMPPClientManagerPBProxy()
            yield self.proxy_smpp.connect(self.host,
                                          self.port,
                                          self.username,
                                          self.password)
        except Exception as e:
            self.proxy_smpp = None
            logger.error(f"Error connecting to Jasmin PB: {e}")

    @defer.inlineCallbacks
    def add_connector(self, params: dict):
        config = SMPPClientConfig(**params)
        yield self.proxy_smpp.add(config)

    @defer.inlineCallbacks
    def start_connector(self, cid: str):
        yield self.proxy_smpp.start(cid)

    @defer.inlineCallbacks
    def stop_connector(self, cid: str):
        yield self.proxy_smpp.stop(cid)

    @defer.inlineCallbacks
    def delete_connector(self, cid: str):
        yield self.proxy_smpp.remove(cid)

    @defer.inlineCallbacks
    def get_connector(self, cid: str):
        connector = yield self.proxy_smpp.connector_details(cid)
        return pickle.loads(connector)

    @defer.inlineCallbacks
    def connector_status(self, cid: str):
        status = yield self.proxy_smpp.service_status(cid)
        return pickle.loads(status)

    @defer.inlineCallbacks
    def execute(self, callback):
        # Start the reactor and call the provided callback
        reactor.callWhenRunning(callback)
        reactor.run()

#  Copyright (c) 2025
#  File created on 2025/4/25
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
from enum import Enum

from django.conf import settings
from jasmin.routing.jasminApi import Group

from quark.jasmin.router_pb import RouterPBInterface
from quark.jasmin.smpp_pb import SmppPBAdapter
from quark.jasmin.utils import to_jsmin_mt_creds, to_jasmin_smpp_creds
from quark.utils.utils import logger

from enum import Enum
from django.db import models
import logging

logger = logging.getLogger(__name__)


class PBType(Enum):
    RouterPB = RouterPBInterface
    SmppPB = SmppPBAdapter


class BaseJasminModel(models.Model):
    """
    Abstract base model for Jasmin-related models with built-in jasmin pb router operations.
    Includes common operations like add/remove groups, enable/disable, and user management.
    """

    class ReactorOperation(Enum):
        # Router PB stuff
        ADD_GROUP = 'add_group'
        REMOVE_GROUP = 'remove_groups'
        GROUP_ENABLE = 'group_enable'
        GROUP_DISABLE = 'group_disable'
        ADD_USER = 'add_user'
        REMOVE_USER = 'remove_user'
        USER_ENABLE = 'user_enable'
        USER_DISABLE = 'user_disable'
        ADD_MT_ROUTE = 'add_mt_route'
        REMOVE_MT_ROUTE = 'remove_mt_route'

        # SMPP PB Stuff

        ADD_SMPP_CONNECTOR = "add_connector"
        REMOVE_SMPP_CONNECTOR = "delete_connector"
        STOP_CONNECTOR = "stop_connector"
        START_CONNECTOR = "start_connector"
        GET_STATUS = "connector_status"
        GET_CONNECTOR = "get_connector"

    def _execute_reactor_operation(self, operation: ReactorOperation, pb_type: PBType, *args, **kwargs):
        """
        Execute a router operation with automatic callback handling
        """
        instance = pb_type.value()
        method = getattr(instance, operation.value)

        try:
            deferred = method(*args, **kwargs)

            # Assign appropriate callbacks based on operation type
            if operation in [
                self.ReactorOperation.ADD_GROUP,
                self.ReactorOperation.ADD_USER,
                self.ReactorOperation.ADD_SMPP_CONNECTOR,
                self.ReactorOperation.ADD_MT_ROUTE,
            ]:
                deferred.addCallbacks(
                    self.handle_write_result,
                    self.handle_write_error
                )
            elif operation in [
                self.ReactorOperation.USER_ENABLE,
                self.ReactorOperation.USER_DISABLE,
                self.ReactorOperation.START_CONNECTOR,
                self.ReactorOperation.STOP_CONNECTOR,
                self.ReactorOperation.GROUP_ENABLE,
                self.ReactorOperation.GROUP_DISABLE
            ]:
                deferred.addCallbacks(
                    self.handle_activate_result,
                    self.handle_activate_error
                )
            else:
                deferred.addCallbacks(
                    self.handle_remove_result,
                    self.handle_remove_error
                )

            instance.set_deferred(deferred)
            instance.execute()
        except Exception as e:
            logger.error(f"Reactor operation failed: {str(e)}")
            raise

    # Result handlers
    def handle_write_result(self, result):
        """Default success handler for write operations"""
        logger.info(f"Write operation succeeded: {result}")

    def handle_write_error(self, error):
        """Default error handler for write operations, if write delete django object"""
        logger.error(f"Write operation failed for {self}: {error}")
        self.delete(run_on_reactor=False)

    def handle_activate_result(self, result):
        """Default success handler for activate operations"""
        logger.info(f"Activate operation succeeded: {result}")
        self.is_active = not self.is_active

        self.save(run_on_reactor=False)

    def handle_activate_error(self, error):
        """Default error handler for write operations, if write delete django object"""
        logger.error(f"Write operation failed: {error}")
        self.is_active = not self.is_active
        self.save(run_on_reactor=False)

    def handle_remove_result(self, result):
        """Default success handler for remove operations delete object if we succeeded"""
        logger.debug(f"Remove remove operation succeeded: {result}")
        self.delete(run_on_reactor=False)

    def handle_remove_error(self, error):
        """Default error handler for remove operations do nothing"""
        logger.error(f"Remove operation on {self} failed: {error} ")

    # Common operation shortcuts
    def jasmin_add_group(self):
        """Add group to Jasmin if instance has a gid property"""
        if hasattr(self, 'gid'):
            self._execute_reactor_operation(
                self.ReactorOperation.ADD_GROUP,
                PBType.RouterPB,
                self.gid,
                settings.JASMIN_PERSIST
            )

    def jasmin_remove_group(self):
        """Remove group from Jasmin"""
        if hasattr(self, 'gid'):
            self._execute_reactor_operation(
                self.ReactorOperation.REMOVE_GROUP,
                PBType.RouterPB,
                self.gid
            )

    def jasmin_enable_group(self):
        """Enable group in Jasmin"""
        if hasattr(self, 'gid'):
            self._execute_reactor_operation(
                self.ReactorOperation.GROUP_ENABLE,
                PBType.RouterPB,
                self.gid
            )

    def jasmin_disable_group(self):
        """Disable group in Jasmin"""
        if hasattr(self, 'gid'):
            self._execute_reactor_operation(
                self.ReactorOperation.GROUP_DISABLE,
                PBType.RouterPB,
                self.gid
            )

    def jasmin_add_user(self, is_new):
        """Add user to Jasmin router"""
        required_attributes = ['username', 'password', 'group', 'mt_credential', 'smpps_credential']
        if all(hasattr(self, attr) for attr in required_attributes):
            mt_creds = to_jsmin_mt_creds(self.mt_credential, is_new)
            smpp_creds = to_jasmin_smpp_creds(self.smpps_credential, is_new)
            self._execute_reactor_operation(
                self.ReactorOperation.ADD_USER,
                PBType.RouterPB,
                self.username,
                self.password,
                Group(self.group.gid),
                mt_creds,
                smpp_creds,
                settings.JASMIN_PERSIST
            )

    def jasmin_remove_user(self):
        if hasattr(self, "username"):
            self._execute_reactor_operation(
                self.ReactorOperation.REMOVE_USER,
                PBType.RouterPB,
                self.username
            )

    def jasmin_add_connector(self):
        jasmin_connector = self.to_smpp_client_config()
        self._execute_reactor_operation(
            self.ReactorOperation.ADD_SMPP_CONNECTOR,
            PBType.SmppPB,
            jasmin_connector,
            settings.JASMIN_PERSIST
        )

    def jasmin_start_connector(self):
        if hasattr(self, "cid"):
            self._execute_reactor_operation(
                self.ReactorOperation.START_CONNECTOR,
                PBType.SmppPB,
                self.cid
            )

    def jasmin_stop_connector(self):
        if hasattr(self, "cid"):
            self._execute_reactor_operation(
                self.ReactorOperation.STOP_CONNECTOR,
                PBType.SmppPB,
                self.cid
            )

    def jasmin_remove_connector(self):
        if hasattr(self, "cid"):
            self._execute_reactor_operation(
                self.ReactorOperation.REMOVE_SMPP_CONNECTOR,
                PBType.SmppPB,
                self.cid,
                settings.JASMIN_PERSIST
            )

    def jasmin_add_mt_route(self):
        route = self.to_jasmin_route()
        self._execute_reactor_operation(
            self.ReactorOperation.ADD_MT_ROUTE,
            PBType.RouterPB,
            route,
                self.order,
            settings.JASMIN_PERSIST
        )

    class Meta:
        abstract = True

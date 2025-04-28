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
from django.db import models
from jasmin.routing.jasminApi import Group

from quark.jasmin.router_pb import RouterPBInterface
from quark.jasmin.utils import to_jsmin_mt_creds, to_jasmin_smpp_creds
from quark.utils.utils import logger

from enum import Enum
from django.db import models
import logging

logger = logging.getLogger(__name__)


class BaseJasminModel(models.Model):
    """
    Abstract base model for Jasmin-related models with built-in jasmin pb router operations.
    Includes common operations like add/remove groups, enable/disable, and user management.
    """

    class RouterOperation(Enum):
        ADD_GROUP = 'add_group'
        REMOVE_GROUP = 'remove_groups'
        GROUP_ENABLE = 'group_enable'
        GROUP_DISABLE = 'group_disable'
        ADD_USER = 'add_user'
        REMOVE_USER = 'remove_user'
        USER_ENABLE = 'user_enable'
        USER_DISABLE = 'user_disable'

    def _execute_router_operation(self, operation: RouterOperation, *args, **kwargs):
        """
        Execute a router operation with automatic callback handling
        """
        router = RouterPBInterface()
        method = getattr(router, operation.value)

        try:
            deferred = method(*args, **kwargs)

            # Assign appropriate callbacks based on operation type
            if operation in [
                self.RouterOperation.ADD_GROUP,
                self.RouterOperation.ADD_USER
            ]:
                deferred.addCallbacks(
                    self.handle_write_result,
                    self.handle_write_error
                )
            else:
                deferred.addCallbacks(
                    self.handle_remove_result,
                    self.handle_remove_error
                )

            router.set_deferred(deferred)
            router.execute()
        except Exception as e:
            logger.error(f"Router operation failed: {str(e)}")
            raise

    # Result handlers
    def handle_write_result(self, result):
        """Default success handler for write operations"""
        logger.debug(f"Write operation succeeded: {result}")

    def handle_write_error(self, error):
        """Default error handler for write operations, if write delete django object"""
        logger.error(f"Write operation failed: {error}")
        self.delete()

    def handle_activate_result(self, result):
        """Default success handler for activate operations"""
        logger.debug(f"Activate operation succeeded: {result}")
        self.is_active = True

    def handle_activate_error(self, error):
        """Default error handler for write operations, if write delete django object"""
        logger.error(f"Write operation failed: {error}")
        self.delete()

    def handle_remove_result(self, result):
        """Default success handler for remove operations delete object if we succeeded"""
        logger.debug(f"Remove remove operation succeeded: {result}")
        self.delete()

    def handle_remove_error(self, error):
        """Default error handler for remove operations do nothing"""
        logger.error(f"Remove operation on {self} failed: {error} ")

    # Common operation shortcuts
    def jasmin_add_group(self):
        """Add group to Jasmin if instance has a gid property"""
        if hasattr(self, 'gid'):
            self._execute_router_operation(
                self.RouterOperation.ADD_GROUP,
                self.gid,
                settings.JASMIN_PERSIST
            )

    def jasmin_remove_group(self):
        """Remove group from Jasmin"""
        if hasattr(self, 'gid'):
            self._execute_router_operation(
                self.RouterOperation.REMOVE_GROUP,
                self.gid
            )

    def jasmin_enable_group(self):
        """Enable group in Jasmin"""
        if hasattr(self, 'gid'):
            self._execute_router_operation(
                self.RouterOperation.GROUP_ENABLE,
                self.gid
            )

    def jasmin_disable_group(self):
        """Disable group in Jasmin"""
        if hasattr(self, 'gid'):
            self._execute_router_operation(
                self.RouterOperation.GROUP_DISABLE,
                self.gid
            )

    def jasmin_add_user(self):
        """Add user to Jasmin router"""
        required_attributes = ['username', 'password', 'group', 'mt_credential', 'smpps_credential']
        if all(hasattr(self, attr) for attr in required_attributes):
            is_new = self.pk is None
            mt_creds = to_jsmin_mt_creds(self.mt_credential, is_new)
            smpp_creds = to_jasmin_smpp_creds(self.smpps_credential, is_new)
            self._execute_router_operation(
                self.RouterOperation.ADD_USER,
                self.username,
                self.password,
                Group(self.group.gid),
                mt_creds,
                smpp_creds,
                settings.JASMIN_PERSIST
            )

    def jasmin_remove_user(self):
        if hasattr(self, "username"):
            self._execute_router_operation(
                self.RouterOperation.REMOVE_USER,
                self.username
            )

    class Meta:
        abstract = True

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
import logging
from enum import Enum

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from jasmin.routing.jasminApi import Group

from quark.jasmin.reactor import run_in_reactor
from quark.jasmin.router_pb import RouterPBInterface
from quark.jasmin.smpp_pb import SmppPBAdapter
from quark.jasmin.utils import to_jsmin_mt_creds, to_jasmin_smpp_creds

logger = logging.getLogger(__name__)


class JasminOperationError(Exception):
    """Raised when Jasmin explicitly rejects an operation (PB returned False)"""


class PBType(Enum):
    RouterPB = RouterPBInterface
    SmppPB = SmppPBAdapter


class BaseJasminModel(models.Model):
    """
    Abstract base model for Jasmin-related models with built-in Jasmin PB operations.

    All operations run synchronously: the calling (request) thread blocks until
    Jasmin confirms or rejects the operation, so success/failure reported to the
    UI is truthful. Failures raise django ValidationError which views can surface
    as form errors.
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
        ADD_ROUTE = 'add_route'
        REMOVE_ROUTE = 'remove_route'
        ADD_INTERCEPTOR = 'add_interceptor'
        REMOVE_INTERCEPTOR = 'remove_interceptor'

        # SMPP PB Stuff
        ADD_SMPP_CONNECTOR = "add_connector"
        UPDATE_SMPP_CONNECTOR = "update_connector"
        REMOVE_SMPP_CONNECTOR = "delete_connector"
        STOP_CONNECTOR = "stop_connector"
        START_CONNECTOR = "start_connector"
        GET_CONNECTOR_STATUS = "connector_status"
        GET_CONNECTOR = "get_connector"

    WRITE_OPERATIONS = (
        ReactorOperation.ADD_GROUP,
        ReactorOperation.ADD_USER,
        ReactorOperation.ADD_SMPP_CONNECTOR,
        ReactorOperation.UPDATE_SMPP_CONNECTOR,
        ReactorOperation.ADD_ROUTE,
        ReactorOperation.ADD_INTERCEPTOR,
    )

    REMOVE_OPERATIONS = (
        ReactorOperation.REMOVE_GROUP,
        ReactorOperation.REMOVE_USER,
        ReactorOperation.REMOVE_SMPP_CONNECTOR,
        ReactorOperation.REMOVE_ROUTE,
        ReactorOperation.REMOVE_INTERCEPTOR,
    )

    # operations whose callers optimistically flip is_active before the PB call,
    # so a failure must revert the flag (see JasminSMPPConnector.start/stop)
    ACTIVATE_OPERATIONS = (
        ReactorOperation.START_CONNECTOR,
        ReactorOperation.STOP_CONNECTOR,
    )

    # read-only operations whose failures must never break page rendering
    READ_OPERATIONS = (
        ReactorOperation.GET_CONNECTOR_STATUS,
        ReactorOperation.GET_CONNECTOR,
    )

    def _execute_reactor_operation(self, operation: ReactorOperation, pb_type: PBType,
                                   *args, rollback_on_error: bool = False, **kwargs):
        """
        Execute a PB operation in the reactor thread and block until Jasmin
        confirms it. Returns the operation result on success.

        On failure:
          - read operations only log (list/detail pages must still render)
          - write operations optionally roll back the local row (new objects only)
          - activate operations revert the local is_active flag
          - all non-read failures raise ValidationError for the UI
        """
        instance = pb_type.value()
        method = getattr(instance, operation.value)

        try:
            result = run_in_reactor(method, *args, **kwargs)
            # Jasmin PB signals rejection by returning False instead of raising.
            # For removes, False means "not found" which is the desired end state,
            # so treat it as success to allow cleaning up out-of-sync rows.
            if result is False and operation not in self.REMOVE_OPERATIONS:
                raise JasminOperationError(
                    f"Jasmin rejected operation '{operation.value}', check jasmin logs for details"
                )
        except Exception as e:
            logger.error(f"Jasmin operation '{operation.value}' failed for {self}: {e}")
            self._handle_operation_error(operation, e, rollback_on_error)
            return None

        return self._handle_operation_success(operation, result)

    def _handle_operation_success(self, operation: ReactorOperation, result):
        if operation in self.REMOVE_OPERATIONS:
            self.handle_remove_result(result)
        elif operation == self.ReactorOperation.GET_CONNECTOR_STATUS:
            self.handle_connector_status(result)
        else:
            logger.info(f"Jasmin operation '{operation.value}' succeeded for {self}")
        return result

    def _handle_operation_error(self, operation: ReactorOperation, error, rollback_on_error: bool):
        if operation in self.READ_OPERATIONS:
            # never break rendering because status could not be fetched
            return

        if operation in self.WRITE_OPERATIONS and rollback_on_error:
            # newly created object could not be applied to Jasmin, remove it locally
            self.delete(run_on_reactor=False)
        elif operation in self.ACTIVATE_OPERATIONS:
            # revert the optimistic is_active flip
            self.is_active = not self.is_active
            self.save(run_on_reactor=False)

        raise ValidationError(f"Jasmin sync failed: {error}")

    # Result handlers
    def handle_remove_result(self, result):
        """Object was removed on Jasmin, remove it locally too"""
        logger.debug(f"Remove operation succeeded: {result}")
        self.delete(run_on_reactor=False)

    def handle_connector_status(self, result):
        """Persist the live connector status if it differs from what we have"""
        if self.is_active != result:
            self.is_active = result
            self.save(run_on_reactor=False)

    # Common operation shortcuts
    def jasmin_add_group(self, is_new: bool = True):
        """Add group to Jasmin if instance has a gid property"""
        if hasattr(self, 'gid'):
            self._execute_reactor_operation(
                self.ReactorOperation.ADD_GROUP,
                PBType.RouterPB,
                self.gid,
                settings.JASMIN_PERSIST,
                rollback_on_error=is_new,
            )

    def jasmin_remove_group(self):
        """Remove group from Jasmin"""
        if hasattr(self, 'gid'):
            self._execute_reactor_operation(
                self.ReactorOperation.REMOVE_GROUP,
                PBType.RouterPB,
                self.gid,
                settings.JASMIN_PERSIST,
            )

    def jasmin_enable_group(self):
        """Enable group in Jasmin"""
        if hasattr(self, 'gid'):
            self._execute_reactor_operation(
                self.ReactorOperation.GROUP_ENABLE,
                PBType.RouterPB,
                self.gid,
                settings.JASMIN_PERSIST,
            )

    def jasmin_disable_group(self):
        """Disable group in Jasmin"""
        if hasattr(self, 'gid'):
            self._execute_reactor_operation(
                self.ReactorOperation.GROUP_DISABLE,
                PBType.RouterPB,
                self.gid,
                settings.JASMIN_PERSIST,
            )

    def jasmin_add_user(self, is_new: bool = True):
        """Add or update user on Jasmin router (Jasmin replaces existing uids)"""
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
                settings.JASMIN_PERSIST,
                rollback_on_error=is_new,
            )

    def jasmin_remove_user(self):
        if hasattr(self, "username"):
            self._execute_reactor_operation(
                self.ReactorOperation.REMOVE_USER,
                PBType.RouterPB,
                self.username,
                settings.JASMIN_PERSIST,
            )

    def jasmin_add_connector(self, is_new: bool = True):
        jasmin_connector = self.to_smpp_client_config()
        operation = (
            self.ReactorOperation.ADD_SMPP_CONNECTOR if is_new
            else self.ReactorOperation.UPDATE_SMPP_CONNECTOR
        )
        self._execute_reactor_operation(
            operation,
            PBType.SmppPB,
            jasmin_connector,
            settings.JASMIN_PERSIST,
            rollback_on_error=is_new,
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

    def jasmin_connector_status(self):
        if hasattr(self, "cid"):
            self._execute_reactor_operation(
                self.ReactorOperation.GET_CONNECTOR_STATUS,
                PBType.SmppPB,
                self.cid)

    def jasmin_remove_connector(self):
        if hasattr(self, "cid"):
            self._execute_reactor_operation(
                self.ReactorOperation.REMOVE_SMPP_CONNECTOR,
                PBType.SmppPB,
                self.cid,
                settings.JASMIN_PERSIST
            )

    def jasmin_add_route(self, is_new: bool = True):
        route = self.to_jasmin_route()
        self._execute_reactor_operation(
            self.ReactorOperation.ADD_ROUTE,
            PBType.RouterPB,
            route,
            self.order,
            self.nature,
            settings.JASMIN_PERSIST,
            rollback_on_error=is_new,
        )

    def jasmin_remove_route(self):
        if hasattr(self, "order") and hasattr(self, "nature"):
            self._execute_reactor_operation(
                self.ReactorOperation.REMOVE_ROUTE,
                PBType.RouterPB,
                self.order,
                self.nature,
                settings.JASMIN_PERSIST
            )

    def jasmin_add_interceptor(self, is_new: bool = True):
        interceptor = self.to_jasmin_interceptor()
        self._execute_reactor_operation(
            self.ReactorOperation.ADD_INTERCEPTOR,
            PBType.RouterPB,
            interceptor,
            self.order,
            self.nature,
            settings.JASMIN_PERSIST,
            rollback_on_error=is_new,
        )

    def jasmin_remove_interceptor(self):
        self._execute_reactor_operation(
            self.ReactorOperation.REMOVE_INTERCEPTOR,
            PBType.RouterPB,
            self.order,
            self.nature,
            settings.JASMIN_PERSIST
        )

    class Meta:
        abstract = True

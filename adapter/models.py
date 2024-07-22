#
#  Copyright (c) 2024
#  File created on 2024/7/18
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
from smartmin.models import SmartModel
from quark.utils import logger, BaseModel
from adapter.router_pb import RouterPBInterface
from jasmin.routing.jasminApi import Group
from twisted.internet import defer, reactor
from django.db import models, transaction
from django.utils.translation import gettext_lazy as _
from typing import Any
from .data_classes import JasminUserConfig
from .tasks import perform_operations_task
from django.conf import settings
import threading

MESSAGING_AUTHORIZATIONS = {
    'http_send': True,
    'http_balance': True,
    'http_rate': True,
    'http_bulk': False,
    'smpps_send': True,
    'http_long_content': True,
    'dlr_level': True,
    'http_dlr_method': True,
    'src_addr': True,
    'priority': True,
    'validity_period': True,
    'schedule_delivery_time': True,
    'hex_content': True
}

MESSAGING_VALUE_FILTERS = {
    'dst_addr': ".*",
    'src_addr': ".*",
    'priority': "^[0-3]$",
    'validity_period': "^\d+$",
    'content': ".*"
}

MESSAGING_DEFAULTS = {
    'src_addr': None
}

MESSAGING_QUOTAS = {
    'balance': "ND",
    'early_percent': "ND",
    'sms_count': "ND",
    'http_throughput': "ND",
    'smpps_throughput': "ND",
    'quotas_updated': False
}

SMPP_AUTHORIZATIONS = {
    'bind': True
}

SMPP_QUOTAS = {
    'max_bindings': "ND"
}


def run_reactor():
    reactor.run(installSignalHandlers=0)


class JasminGroup(BaseModel):
    gid = models.CharField(
        max_length=255,
        unique=True,
        null=False,
        db_index=True,
        help_text=_("This matches the group id created in Jasmin"),
        verbose_name=_("Group Id")
    )

    def __str__(self):
        return self.gid

    def handle_result(self, result):
        logger.info("Result from Twisted operation:")

    def handle_error(self, error):
        logger.error("Error in Twisted operation:")

    def save(self, *args, **kwargs):
        # Save the Django model first
        super().save(*args, **kwargs)
        logger.info(f"Twisted reactor: {reactor.running}")
        router = RouterPBInterface()
        router.set_deferred(router.add_group(self.gid))
        router.execute()

    class Meta:
        db_table = 'jasmin_group'


class JasminUser(BaseModel):
    username = models.CharField(
        max_length=255,
        unique=True,
        null=False,
        help_text=_("This matches the user username created in Jasmin"),
        verbose_name=_("Username")
    )
    password = models.CharField(
        max_length=255,
        help_text=_("We shall store this password in clear text here"),
        verbose_name=_("Password")
    )
    group = models.ForeignKey(JasminGroup, on_delete=models.CASCADE)
    enabled = models.BooleanField(default=True)
    mt_credential = models.JSONField(default=dict, blank=True)
    smpps_credential = models.JSONField(default=dict, blank=True)

    def save(self, *args, **kwargs):
        if self.mt_credential is None or self.mt_credential == {}:
            self.mt_credential = {
                'authorization': MESSAGING_AUTHORIZATIONS,
                'valuefilter': MESSAGING_VALUE_FILTERS,
                'defaultvalue': MESSAGING_DEFAULTS,
                'quota': MESSAGING_QUOTAS,
            }

        if self.smpps_credential is None or self.smpps_credential == {}:
            self.smpps_credential = {
                'authorization': SMPP_AUTHORIZATIONS,
                'quota': SMPP_QUOTAS,
            }
        is_new = self.pk is None
        super().save(*args, **kwargs)

    def __str__(self):
        return self.username

    class Meta:
        db_table = 'jasmin_user'

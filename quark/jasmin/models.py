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
from django.conf import settings
from jasmin.routing.jasminApi import Group, MtMessagingCredential
from smartmin.models import SmartModel

from quark.jasmin.utils import to_jsmin_mt_creds, to_jasmin_smpp_creds
from quark.utils.jasmin.extras import BaseJasminModel
from quark.utils.utils import logger
from quark.jasmin.router_pb import RouterPBInterface
from twisted.internet import reactor
from django.db import models
from django.utils.translation import gettext_lazy as _

MESSAGING_AUTHORIZATIONS = {
    'http_send': True,
    'http_balance': True,
    'http_rate': True,
    'http_bulk': False,
    'smpps_send': True,
    'http_long_content': True,
    'set_dlr_level': True,
    'http_set_dlr_method': True,
    'set_source_address': True,
    'set_priority': True,
    'set_validity_period': True,
    'set_schedule_delivery_time': True,
    'set_hex_content': True
}

MESSAGING_VALUE_FILTERS = {
    'destination_address': ".*",
    'source_address': ".*",
    'priority': "^[0-3]$",
    'validity_period': "^\d+$",
    'content': ".*"
}

MESSAGING_DEFAULTS = {
    'source_address': None
}

MESSAGING_QUOTAS = {
    'balance': None,
    'early_decrement_balance_percent': None,
    'submit_sm_count': None,
    'http_throughput': None,
    'smpps_throughput': None,
    'quota_updated': False
}

SMPP_AUTHORIZATIONS = {
    'bind': True
}

SMPP_QUOTAS = {
    'max_bindings': "ND"
}


def run_reactor():
    reactor.run(installSignalHandlers=0)


class JasminGroup(BaseJasminModel, SmartModel):
    gid = models.CharField(
        max_length=16,  # we are restricted by jasmin 16
        unique=True,
        null=False,
        db_index=True,

        help_text=_("This matches the group id created in Jasmin and will be prefixed with Workspace's prefix"),
        verbose_name=_("Group Id")
    )
    workspace = models.ForeignKey("workspace.WorkSpace", related_name="jasmin_groups", on_delete=models.CASCADE,
                                  null=True)
    description = models.TextField(
        null=True,
        help_text=_("Short description about purpose of this group."),
        verbose_name=_("Description"),
        blank=True)

    def __str__(self):
        return self.gid

    @classmethod
    def create(cls, gid: str, user, workspace, description: str):

        return JasminGroup.objects.create(
            gid=gid,
            workspace=workspace,
            description=description,
            created_by=user,
            modified_by=user
        )

    def save(self, *args, **kwargs):
        # Save the Django model first
        super().save(*args, **kwargs)
        self.jasmin_add_group()

    def delete(self, using=None, keep_parents=False):
        self.jasmin_remove_group()

    @classmethod
    def map_from_jasmin(cls, jasmin_group):
        group = None
        try:
            group = cls.objects.get(gid=jasmin_group)
        except Exception as e:
            logger.error(e)
        return group

    @classmethod
    def map_bulk_from_jasmin(cls, group_list):
        groups = []
        for group in group_list:
            g = cls.map_from_jasmin(group)
            if g is not None:
                groups.append(g)
        return groups

    def activate(self):
        if self.is_active:
            raise Exception("Group already activated")
        self.is_active = True
        self.jasmin_enable_group()

    def deactivate(self):
        if not self.is_active:
            raise Exception("Group already deactivated")
        self.is_active = False
        self.jasmin_disable_group()

    class Meta:
        db_table = 'jasmin_group'


class JasminUser(SmartModel, BaseJasminModel):
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
                'authorizations': MESSAGING_AUTHORIZATIONS,
                'value_filters': MESSAGING_VALUE_FILTERS,
                'defaults': MESSAGING_DEFAULTS,
                'quotas': MESSAGING_QUOTAS,
            }

        if self.smpps_credential is None or self.smpps_credential == {}:
            self.smpps_credential = {
                'authorizations': SMPP_AUTHORIZATIONS,
                'quotas': SMPP_QUOTAS,
            }
        super().save(*args, **kwargs)
        self.jasmin_add_user()

    def delete(self, using=None, keep_parents=False):
        self.jasmin_remove_user()

    def __str__(self):
        return self.username

    class Meta:
        db_table = 'jasmin_user'

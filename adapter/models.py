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
from twisted.internet import defer
from django.db import models, transaction
from django.utils.translation import gettext_lazy as _
from typing import Any


class JasminGroup(BaseModel):
    gid = models.CharField(
        max_length=255,
        unique=True,
        null=True,
        db_index=True,
        help_text=_("This matches the group id created in Jasmin"),
        verbose_name=_("Group Id")
    )

    def __str__(self):
        return self.gid

    @classmethod
    def create(cls, gid: str) -> Any | None:
        instance = cls.objects.create(gid=gid)
        return instance

    class Meta:
        db_table = 'jasmin_group'

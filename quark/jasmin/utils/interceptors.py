#  Copyright (c) 2025
#  File created on 2025/5/4
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

from django.db import models
from jasmin.routing.Interceptors import (
    DefaultInterceptor,
    StaticMTInterceptor,
    StaticMOInterceptor,
)

MO = "MO"
MT = "MT"


class MTInterceptorType(Enum):
    DefaultInterceptor = DefaultInterceptor, (
        "An interceptor without a filter, this one can only be set with the lowest order "
        "to be a default/fallback interceptor"
    )
    StaticMTInterceptor = StaticMTInterceptor, (
        "A basic interceptor with Filters and one Script, applied to outbound (MT) messages "
        "before routing"
    )

    @classmethod
    def jasmin_class(cls, field):
        return cls[field].value[0]


class MOInterceptorType(Enum):
    DefaultInterceptor = DefaultInterceptor, (
        "An interceptor without a filter, this one can only be set with the lowest order "
        "to be a default/fallback interceptor"
    )
    StaticMOInterceptor = StaticMOInterceptor, (
        "A basic interceptor with Filters and one Script, applied to inbound (MO) messages "
        "before routing"
    )

    @classmethod
    def jasmin_class(cls, field):
        return cls[field].value[0]


class InterceptorChoice(models.TextChoices):
    DefaultInterceptor = "DefaultInterceptor", "Default Interceptor"
    StaticMOInterceptor = "StaticMOInterceptor", "Static MO Interceptor"
    StaticMTInterceptor = "StaticMTInterceptor", "Static MT Interceptor"


class JasminBaseInterceptor(models.Model):
    """
    Shared fields for Jasmin MO/MT interceptors.

    Per the official docs, MO and MT interception tables are separate. Each entry
    is ordered and holds filters (optional for DefaultInterceptor) plus a python
    script that Jasmin copies into its core when the rule is added.
    """
    nature = models.CharField(
        max_length=2,
        choices=[(MO, "MO"), (MT, "MT")],
        help_text="MO intercepts inbound SMS before routing; MT intercepts outbound SMS before routing.",
    )
    interceptor_type = models.CharField(
        max_length=30,
        choices=InterceptorChoice.choices,
        default=InterceptorChoice.DefaultInterceptor,
        help_text="DefaultInterceptor (order 0, no filters) or StaticMO/StaticMTInterceptor.",
    )
    order = models.IntegerField(
        help_text="Interceptor order. DefaultInterceptor is always order 0 (lowest / fallback).",
    )
    workspace = models.ForeignKey("workspace.WorkSpace", on_delete=models.CASCADE)

    class Meta:
        abstract = True

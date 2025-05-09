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
    StaticMOInterceptor
)


class InterceptorType(Enum):
    DefaultInterceptor = DefaultInterceptor
    StaticMOInterceptor = StaticMOInterceptor
    StaticMTInterceptor = StaticMTInterceptor

    @classmethod
    def jasmin_class(cls, field):
        return cls[field].value


class InterceptorChoice(models.TextChoices):
    DefaultInterceptor = "DefaultInterceptor", "Default Interceptor",
    StaticMOInterceptor = "StaticMOInterceptor", "Static MO Interceptor",
    StaticMTInterceptor = "StaticMTInterceptor", "Static MT Interceptor",


class JasminBaseInterceptor(models.Model):
    nature = models.CharField(
        max_length=2,
        choices=[("MO", "MO"), ("MT", "MT")],
    )

    interceptor_type = models.CharField(
        max_length=30,
        choices=InterceptorChoice.choices,
        default=InterceptorChoice.DefaultInterceptor,
    )
    order = models.IntegerField(unique=True)

    workspace = models.ForeignKey("workspace.WorkSpace", on_delete=models.CASCADE)

    class Meta:
        abstract = True

#  Copyright (c) 2025
#  File created on 2025/5/3
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
import re
import os
from datetime import datetime
from enum import Enum
from typing import Any, Dict

from django.db import models
from jasmin.routing.Filters import *

from quark.jasmin.utils import StructuredJSONField

FilterKeyMap = {'fid': 'fid', 'type': 'type'}

MO = "MO"
MT = "MT"
ALL = "ALL"

FILTER_TYPE = [
    (MO, "Mobile Originated"),
    (MT, "Mobile Terminated"),
    (ALL, "All"),
]


class FilterValidationError(Exception):
    """Custom exception for filter validation errors"""
    pass


class BaseFilterValidator:
    """Single source of truth for all filter validation"""

    VALIDATORS = {
        'TransparentFilter': (lambda v: None, False),
        'ConnectorFilter': (lambda v: str(v).strip(), True),
        'UserFilter': (lambda v: str(v).strip(), True),
        'GroupFilter': (lambda v: str(v).strip(), True),
        'SourceAddrFilter': (lambda v: validate_regex(v), True),
        'DestinationAddrFilter': (lambda v: validate_regex(v), True),
        'ShortMessageFilter': (lambda v: validate_regex(v), True),
        'DateIntervalFilter': (lambda v: validate_date_interval(v), True),
        'TimeIntervalFilter': (lambda v: validate_time_interval(v), True),
        'TagFilter': (lambda v: int(v), True),
        'EvalPyFilter': (lambda v: validate_py_script(v), True),
    }

    @classmethod
    def validate_parameter(cls, key: str, value: Any) -> Any:
        filter_type = key

        try:
            validator, required = cls.VALIDATORS[filter_type]
        except KeyError:
            raise FilterValidationError(f"Unknown filter type: {filter_type}")

        if required and value is None:
            raise FilterValidationError(f"{filter_type} requires a parameter")
        if not required and value is not None:
            raise FilterValidationError(f"{filter_type} doesn't accept parameters")

        try:
            return validator(value) if value is not None else None
        except Exception as e:
            raise FilterValidationError(f"Invalid parameter for {filter_type}: {str(e)}")


def validate_regex(v):
    v_str = str(v).strip()
    # test compilation but return original value
    re.compile(v_str)
    return v_str


# Helper validation functions
def validate_date_interval(value):
    dates = value.split(';')
    if len(dates) != 2:
        raise ValueError("Need exactly two dates separated by ';'")
    start, end = [datetime.strptime(d.strip(), "%Y-%m-%d").date() for d in dates]
    if start > end:
        raise ValueError("Start date must be before end date")
    return f"{start};{end}"


def validate_time_interval(value):
    times = value.split(';')
    if len(times) != 2:
        raise ValueError("Need exactly two times (HH:MM:SS;HH:MM:SS)")
    start, end = (datetime.strptime(t.strip(), "%H:%M:%S").time() for t in times)
    return f"{start};{end}"


def validate_py_script(value):
    if not os.path.exists(value):
        raise ValueError("File does not exist")
    if not value.endswith('.py'):
        raise ValueError("Must be a Python script (.py)")
    return value


class MoFilters(BaseFilterValidator, Enum):
    ConnectorFilter = ConnectorFilter, "Will match the source connector of a message"

    @classmethod
    def validate(cls, filter_type: str, value: Any) -> Any:
        return cls[filter_type].validate_parameter(filter_type, value)


class MTFilters(BaseFilterValidator, Enum):
    UserFilter = UserFilter, "Will match the owner of a MT message"
    GroupFilter = GroupFilter, "Will match the owner’s group of a MT message"

    @classmethod
    def validate(cls, filter_type: str, value: Any) -> Any:
        return cls[filter_type].validate_parameter(filter_type, value)


class AllFilters(BaseFilterValidator, Enum):
    TransparentFilter = TransparentFilter, "This filter will always match any message criteria"
    SourceAddrFilter = SourceAddrFilter, "Will match the source address of a MO message"
    DestinationAddrFilter = DestinationAddrFilter, "Will match the destination address of a MT message"
    ShortMessageFilter = DestinationAddrFilter, "Will match the content of a message"
    DateIntervalFilter = DateIntervalFilter, "Will match the date of a message"
    TimeIntervalFilter = TimeIntervalFilter, "Will match the time of a message"
    TagFilter = TagFilter, "Will check if message has a defined tag"
    EvalPyFilter = EvalPyFilter, ("Will pass the message to a third party python script for user-defined "
                                  "filtering")

    @classmethod
    def validate(cls, filter_type: str, value: Any) -> Any:
        return cls[filter_type].validate_parameter(filter_type, value)


class JasminBaseFilter(models.Model):
    """
    This proxy model represents a jasmin filter all filters will inherit it
    """
    fid = models.CharField(
        max_length=64,
        unique=True,
        help_text="The Jasmin unique filter id",
    )
    nature = models.CharField(
        max_length=3,
        choices=FILTER_TYPE,
        default=ALL,
        help_text="Whether a filter applies to MO, MT or ALL messages",
    )

    param = StructuredJSONField(
        max_length=100,
        null=True,
        blank=True,
        help_text="For a given filter type, additional parameters may be required. Must be in format {'key': '', "
                  "'value': ''}",
    )
    workspace = models.ForeignKey("workspace.WorkSpace", on_delete=models.CASCADE)

    class Meta:
        abstract = True

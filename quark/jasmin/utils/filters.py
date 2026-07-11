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
import os
import re
from datetime import datetime
from enum import Enum
from typing import Any

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
        # EvalPyFilter stores Python source in DB (same idea as interceptors).
        # Jasmin's EvalPyFilter(pyCode=...) expects source text, not a file path.
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
    """
    Validate EvalPyFilter pyCode.

    Accepts Python source text (preferred). For backwards compatibility, if the
    value looks like a filesystem path to an existing .py file, read and return
    its contents (mirroring what jcli does with `pyCode /path/to/script.py`).
    """
    if value is None:
        raise ValueError("pyCode source is required")

    source = value
    if isinstance(source, bytes):
        source = source.decode("utf-8")
    source = str(source)

    stripped = source.strip()
    if not stripped:
        raise ValueError("pyCode source is empty")

    # Legacy: stored path instead of source — read the file once (jcli behaviour)
    looks_like_path = (
        "\n" not in stripped
        and stripped.endswith(".py")
        and (stripped.startswith("/") or stripped.startswith("./") or "\\" in stripped)
    )
    if looks_like_path:
        if os.path.isfile(stripped):
            with open(stripped, "r", encoding="utf-8", errors="replace") as handle:
                source = handle.read()
            stripped = source.strip()
            if not stripped:
                raise ValueError(f"Script file is empty: {value}")
        else:
            raise ValueError(
                "EvalPyFilter expects Python source code stored in Joyce. "
                f"Path '{stripped}' was not found. Paste the script or upload a .py file."
            )

    try:
        compile(stripped, "<EvalPyFilter>", "exec")
    except SyntaxError as exc:
        raise ValueError(f"Script has a syntax error: {exc}") from exc

    return stripped


class MoFilters(BaseFilterValidator, Enum):
    ConnectorFilter = ConnectorFilter, Connector

    @classmethod
    def validate(cls, filter_type: str, value: Any) -> Any:
        return cls[filter_type].validate_parameter(filter_type, value)


class MTFilters(BaseFilterValidator, Enum):
    UserFilter = UserFilter, User
    GroupFilter = GroupFilter, Group

    @classmethod
    def validate(cls, filter_type: str, value: Any) -> Any:
        return cls[filter_type].validate_parameter(filter_type, value)


class AllFilters(BaseFilterValidator, Enum):
    # we have already validated these so let's just use None and empty lists
    TransparentFilter = TransparentFilter, None
    SourceAddrFilter = SourceAddrFilter, []
    DestinationAddrFilter = DestinationAddrFilter, []
    ShortMessageFilter = ShortMessageFilter, []
    DateIntervalFilter = DateIntervalFilter, []
    TimeIntervalFilter = TimeIntervalFilter, []
    TagFilter = TagFilter, []
    EvalPyFilter = EvalPyFilter, []

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
        null=True,
        blank=True,
        help_text=(
            "Filter parameter as {'key': '...', 'value': '...'}. "
            "For EvalPyFilter, key is pyCode and value is the Python source stored in the DB."
        ),
    )
    workspace = models.ForeignKey("workspace.WorkSpace", on_delete=models.CASCADE)

    class Meta:
        abstract = True

#
#  Copyright (c) 2024
#  File created on 2024/7/17
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
import threading
from typing import Any
from django.db import models
from django.contrib.auth.models import User

logger = logging.getLogger('main')


_thread_locals = threading.local()


def set_current_user(user):
    _thread_locals.user = user


def get_current_user():
    return getattr(_thread_locals, 'user', None)


def remove_current_user():
    _thread_locals.user = None


def to_dict(obj: Any) -> dict:
    if not hasattr(obj, "__dict__"):
        return obj

    result = {}

    for key, val in obj.__dict__.items():
        if key.startswith("_"):
            continue

        if isinstance(val, list):
            # Handle lists of objects recursively
            element = [to_dict(item) for item in val]
        else:
            # Recursively convert non-list attributes
            element = to_dict(val)

        if key in result:
            # If key already exists in result, convert to list if not already
            if not isinstance(result[key], list):
                result[key] = [result[key]]
            result[key].append(element)
        else:
            result[key] = element

    return result


class BaseModel(models.Model):
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=False, editable=False,
                                   related_name='%(class)s_created')
    modified_by = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=False, editable=False,
                                    related_name='%(class)s_modified')
    created_on = models.DateTimeField(auto_now_add=True, db_index=True, blank=False, null=True)
    modified_on = models.DateTimeField(auto_now=True, db_index=True, blank=False, null=True)

    def save(self, *args, **kwargs):
        user = get_current_user()
        if user and user.is_authenticated:
            self.modified_by = user
            if not self.id:
                self.created_by = user
        super(BaseModel, self).save(*args, **kwargs)

    class Meta:
        abstract = True

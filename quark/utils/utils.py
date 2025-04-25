import json
import pandas as pd
import logging
import threading
from typing import Any
from django.db import models
from django.contrib.auth.models import User

logger = logging.getLogger(__name__)


def prep_json_list_data(data: list):
    """
    converts list of dicts to json
    :param data:
    :return:
    """
    if isinstance(data, list):
        return json.dumps(data)
    return []


def strprice(price):
    """
    rounds price to 4 decimal places
    :param price:
    :return:
    """
    return float(format(float(price), '.4f'))


def to_lowercase(d: dict):
    """

    :param d:
    :return:
    """
    return {k.lower(): v for k, v in d.items()}


def read_csv(file_path):
    """
    :param file_path:
    :return:
    """
    try:
        if not file_path:
            logger.error("No file path provided for CSV reading")
            return []
        # Read the CSV file into a pandas DataFrame
        return pd.read_csv(file_path, encoding='utf-8')

    except FileNotFoundError:
        logger.error(f'CSV File not found at: {file_path}')
        return None
    except pd.errors.EmptyDataError:
        logger.error(f'CSV file at {file_path} is empty')
        return None
    except Exception as e:
        logger.error(f'Error reading CSV file at {file_path}: {str(e)}')
        return None


def str_to_bool(text):
    """
    Parses a boolean value from the given text
    """
    return text and text.lower() in ["true", "y", "yes", "1"]


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

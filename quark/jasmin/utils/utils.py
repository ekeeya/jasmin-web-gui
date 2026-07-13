#  Copyright (c) 2025
#  File created on 2025/4/28
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

from django.core.exceptions import ValidationError
from django.db import models
from jasmin.routing.jasminApi import MtMessagingCredential, SmppsCredential
from smpp.pdu.pdu_types import AddrTon, AddrNpi, PriorityFlag, RegisteredDeliveryReceipt, ReplaceIfPresentFlag


class StructuredJSONField(models.JSONField):
    """Custom JSONField that enforces {"key": "", "value": ""} structure"""

    def validate(self, value, model_instance):
        super().validate(value, model_instance)
        if value is not None:  # Allow null/blank
            if not isinstance(value, dict):
                raise ValidationError("Param must be a JSON object/dictionary")
            if set(value.keys()) != {'key', 'value'}:
                raise ValidationError('Param must have exactly two keys: "key" and "value"')
            if not isinstance(value.get('key'), str) or not isinstance(value.get('value'),
                                                                       (str, int, float, bool, type(None))):
                raise ValidationError(
                    'Param "key" must be a string and "value" must be a string, number, boolean or null')


def _coerce_mt_quota(key, value):
    """
    Jasmin decrements balance/throughput with floats (route rates).
    If balance is stored as int, updateQuota raises:
      Type mismatch, cannot update an int with a float value
    """
    if value is None:
        return None
    if key in ("balance", "http_throughput", "smpps_throughput"):
        return float(value)
    if key in ("submit_sm_count", "early_decrement_balance_percent"):
        return int(value)
    return value


def to_jsmin_mt_creds(creds: dict, is_new: bool) -> MtMessagingCredential:
    """
    Build MtMessagingCredential for RouterPB user_add.

    Always use setQuota for absolute values. Jasmin's updateQuota() *increments*
    a quota (billing delta) and is wrong when replacing a user via user_add.
    ``is_new`` is kept for call-site compatibility.
    """
    jasmin_mt_creds = MtMessagingCredential()
    for key, section in (creds or {}).items():
        if not isinstance(section, dict):
            continue
        for k, v in section.items():
            if key == "authorizations":
                jasmin_mt_creds.setAuthorization(k, v)
            elif key == "value_filters":
                jasmin_mt_creds.setValueFilter(k, v)
            elif key == "defaults":
                jasmin_mt_creds.setDefaultValue(k, v)
            else:
                jasmin_mt_creds.setQuota(k, _coerce_mt_quota(k, v))
    return jasmin_mt_creds


def to_jasmin_smpp_creds(creds: dict, is_new: bool) -> SmppsCredential:
    """Build SmppsCredential for RouterPB user_add (absolute quotas via setQuota)."""
    jasmin_smpp_creds = SmppsCredential()
    for key, section in (creds or {}).items():
        if not isinstance(section, dict):
            continue
        for k, v in section.items():
            if key == "authorizations":
                jasmin_smpp_creds.setAuthorization(k, v)
            else:
                jasmin_smpp_creds.setQuota(k, v)
    return jasmin_smpp_creds


def _pattern_to_str(value_filter) -> str:
    """Normalize Jasmin compiled regex / pattern to a form-friendly string."""
    if value_filter is None:
        return ".*"
    pattern = getattr(value_filter, "pattern", value_filter)
    if isinstance(pattern, bytes):
        return pattern.decode("utf-8", errors="replace")
    return str(pattern)


def from_jasmin_mt_creds(mt_cred: MtMessagingCredential) -> dict:
    """Convert a live Jasmin MtMessagingCredential into Django mt_credential JSON."""
    authorizations = {
        key: mt_cred.getAuthorization(key) for key in mt_cred.authorizations.keys()
    }
    value_filters = {
        key: _pattern_to_str(mt_cred.getValueFilter(key))
        for key in mt_cred.value_filters.keys()
    }
    defaults = {
        key: mt_cred.getDefaultValue(key) for key in mt_cred.defaults.keys()
    }
    # Skip internal bookkeeping keys (e.g. quotas_updated) — only real quotas.
    quotas = {
        key: mt_cred.getQuota(key)
        for key in mt_cred.quotas.keys()
        if key != "quotas_updated"
    }
    return {
        "authorizations": authorizations,
        "value_filters": value_filters,
        "defaults": defaults,
        "quotas": quotas,
    }


def from_jasmin_smpp_creds(smpp_cred: SmppsCredential) -> dict:
    """Convert a live Jasmin SmppsCredential into Django smpps_credential JSON."""
    authorizations = {
        key: smpp_cred.getAuthorization(key) for key in smpp_cred.authorizations.keys()
    }
    quotas = {
        key: smpp_cred.getQuota(key) for key in smpp_cred.quotas.keys()
    }
    return {
        "authorizations": authorizations,
        "quotas": quotas,
    }


TON_VALUES = {
    "0": AddrTon.UNKNOWN,
    "1": AddrTon.INTERNATIONAL,
    "2": AddrTon.NATIONAL,
    "3": AddrTon.NETWORK_SPECIFIC,
    "4": AddrTon.SUBSCRIBER_NUMBER,
    "5": AddrTon.ALPHANUMERIC,
    "6": AddrTon.ABBREVIATED,
}

NPI_VALUES = {
    "0": AddrNpi.UNKNOWN,
    "1": AddrNpi.ISDN,
    "3": AddrNpi.DATA,
    "4": AddrNpi.TELEX,
    "5": AddrNpi.LAND_MOBILE,
    "8": AddrNpi.NATIONAL,
    "9": AddrNpi.PRIVATE,
    "10": AddrNpi.ERMES,
    "14": AddrNpi.INTERNET,
    "18": AddrNpi.WAP_CLIENT_ID,
}

PRIORITY_VALUES = {
    "0": PriorityFlag.LEVEL_0,
    "1": PriorityFlag.LEVEL_1,
    "2": PriorityFlag.LEVEL_2,
    "3": PriorityFlag.LEVEL_3
}
REGISTERED_DELIVERY_VALUES = {
    "0": RegisteredDeliveryReceipt.NO_SMSC_DELIVERY_RECEIPT_REQUESTED,
    "1": RegisteredDeliveryReceipt.SMSC_DELIVERY_RECEIPT_REQUESTED,
    "2": RegisteredDeliveryReceipt.SMSC_DELIVERY_RECEIPT_REQUESTED_FOR_FAILURE
}

REPLACE_IF_PRESENT_VALUES = {
    "0": ReplaceIfPresentFlag.DO_NOT_REPLACE,
    "1": ReplaceIfPresentFlag.REPLACE,
}

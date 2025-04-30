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
import re

from jasmin.protocols.cli.smppccm import JCliSMPPClientConfig
from jasmin.routing.jasminApi import MtMessagingCredential, SmppsCredential
from smpp.pdu.pdu_types import AddrTon, AddrNpi


def to_jsmin_mt_creds(creds: dict, is_new: bool) -> MtMessagingCredential:
    jasmin_mt_creds = MtMessagingCredential()
    for key, value in creds.items():
        iterator = creds[key].items()
        for k, v in iterator:
            if key == "authorizations":
                jasmin_mt_creds.setAuthorization(k, v)
            elif key == "value_filters":
                jasmin_mt_creds.setValueFilter(k, v)
            elif key == "defaults":
                jasmin_mt_creds.setDefaultValue(k, v)
            else:
                jasmin_mt_creds.setQuota(k, v) if is_new else jasmin_mt_creds.updateQuota(k, v)
    return jasmin_mt_creds


def to_jasmin_smpp_creds(creds: dict, is_new: bool) -> SmppsCredential:
    jasmin_smpp_creds = SmppsCredential()
    for key, value in creds.items():
        iterator = creds[key].items()
        for k, v in iterator:
            if key == "authorizations":
                jasmin_smpp_creds.setAuthorization(k, v)
            else:
                jasmin_smpp_creds.setQuota(k, v) if is_new else jasmin_smpp_creds.updateQuota(k, v)
    return jasmin_smpp_creds


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


def to_smpp_client_config(connector) -> JCliSMPPClientConfig:
    """Convert Django model instance to SMPPClientConfig"""
    connector_id = f"smppc_{connector.workspace.id}_{str(connector.id)}"
    params = {
        'id': connector_id,
        'port': connector.port,
        'host': connector.host,
        'username': connector.username,
        'password': connector.password,
        'systemType': connector.system_type,
        'log_file': connector.log_file,
        'log_rotate': connector.log_rotate,
        'log_level': connector.log_level,
        'log_privacy': connector.log_privacy,
        'sessionInitTimerSecs': connector.session_init_timer_secs,
        'enquireLinkTimerSecs': connector.enquire_link_timer_secs,
        'inactivityTimerSecs': connector.inactivity_timer_secs,
        'responseTimerSecs': connector.response_timer_secs,
        'pduReadTimerSecs': connector.pdu_read_timer_secs,
        'dlr_expiry': connector.dlr_expiry,
        'reconnectOnConnectionLoss': connector.reconnect_on_connection_loss,
        'reconnectOnConnectionFailure': connector.reconnect_on_connection_failure,
        'reconnectOnConnectionLossDelay': connector.reconnect_on_connection_loss_delay,
        'reconnectOnConnectionFailureDelay': connector.reconnect_on_connection_failure_delay,
        'useSSL': connector.use_ssl,
        'SSLCertificateFile': connector.ssl_certificate_file,
        'bindOperation': connector.bind_operation,
        'source_addr': connector.source_addr,
        'source_addr_ton': TON_VALUES[str(connector.source_addr_ton)],
        'source_addr_npi': NPI_VALUES[str(connector.source_addr_npi)],
        'dest_addr_ton': TON_VALUES[str(connector.dest_addr_ton)],
        'dest_addr_npi': NPI_VALUES[str(connector.dest_addr_npi)],
        'addressTon': TON_VALUES[str(connector.address_ton)],
        'addressNpi': NPI_VALUES[str(connector.address_npi)],
        'addressRange': connector.address_range,
        'validity_period': connector.validity_period,
        'priority_flag': connector.priority_flag,
        'registered_delivery': connector.registered_delivery,
        'replace_if_present_flag': connector.replace_if_present_flag,
        'data_coding': connector.data_coding,
        'requeue_delay': connector.requeue_delay,
        'submit_sm_throughput': connector.submit_sm_throughput,
        'dlr_msg_id_bases': connector.dlr_msg_id_bases,
    }
    if params["log_file"] is None:
        # if log file is not set leave it upto jasmin to default it
        del params['log_file']

    return JCliSMPPClientConfig(**params)

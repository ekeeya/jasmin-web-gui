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
import logging
import uuid
from time import sleep

from django.db import models
from django.utils.translation import gettext_lazy as _
from jasmin.protocols.cli.smppccm import JCliSMPPClientConfig
from jasmin.routing.Routes import DefaultRoute, StaticMTRoute, RandomRoundrobinMTRoute, FailoverMTRoute, \
    RandomRoundrobinMORoute, StaticMORoute, FailoverMORoute
from jasmin.routing.jasminApi import Connector, SmppClientConnector
from smartmin.models import SmartModel
from smpp.pdu.constants import *
from smpp.pdu.pdu_types import RegisteredDelivery

from quark.jasmin.utils import PRIORITY_VALUES, TON_VALUES, NPI_VALUES, REGISTERED_DELIVERY_VALUES, \
    REPLACE_IF_PRESENT_VALUES
from quark.jasmin.utils.filters import JasminBaseFilter, MO, MoFilters, MTFilters, MT, AllFilters
from quark.jasmin.utils.routers import JasminBaseRouter, MTRouterChoices, MTRouter, MORouter
from quark.utils.jasmin.extras import BaseJasminModel
from quark.utils.utils import logger

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
        run_on_reactor = kwargs.pop('run_on_reactor', True)
        # Save the Django model first
        super().save(*args, **kwargs)
        if run_on_reactor:
            self.jasmin_add_group()

    def delete(self, *args, **kwargs):
        run_on_reactor = kwargs.pop('run_on_reactor', True)
        if run_on_reactor:
            self.jasmin_remove_group()
        else:
            super().delete(*args, **kwargs)

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
        self.jasmin_enable_group()

    def deactivate(self):
        if not self.is_active:
            raise Exception("Group already deactivated")
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
        run_on_reactor = kwargs.pop('run_on_reactor', True)
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if run_on_reactor:
            self.jasmin_add_user(is_new)

    def delete(self, *args, **kwargs):
        run_on_reactor = kwargs.pop('run_on_reactor', True)
        if run_on_reactor:
            self.jasmin_remove_user()
        else:
            super().delete(*args, **kwargs)

    def __str__(self):
        return self.username

    class Meta:
        db_table = 'jasmin_user'


class JasminSMPPConnector(BaseJasminModel, SmartModel):
    """
    Represents a Jasmin SMPP client connector
    """
    # Log rotation choices
    SECONDS = "S"
    MINUTES = "M"
    HOURS = "H"
    DAYS = "D"
    WEEKEND = "W0-W6"
    MIDNIGHT = "midnight"

    LOG_ROTATE_CHOICES = [
        (SECONDS, "Seconds"),
        (MINUTES, "Minutes"),
        (HOURS, "Hours"),
        (DAYS, "Days"),
        (WEEKEND, "Weekend"),
        (MIDNIGHT, "Midnight"),
    ]

    # Bind type choices
    TRANSCEIVER = "transceiver"
    RECEIVER = "receiver"
    TRANSMITTER = "transmitter"
    BIND_TYPES = [
        (TRANSCEIVER, TRANSCEIVER),
        (RECEIVER, RECEIVER),
        (TRANSMITTER, TRANSMITTER),
    ]

    # TON (Type of Number) choices
    UNKNOWN = 0
    INTERNATIONAL = 1
    NATIONAL = 2
    NETWORK_SPECIFIC = 3
    SUBSCRIBER_NUMBER = 4
    ALPHANUMERIC = 5
    ABBREVIATED = 6

    TON_VALUES = [
        (UNKNOWN, "Unknown"),
        (INTERNATIONAL, "International"),
        (NATIONAL, "National"),
        (NETWORK_SPECIFIC, "Network Specific"),
        (SUBSCRIBER_NUMBER, "Subscriber Number"),
        (ALPHANUMERIC, "Alphanumeric"),
        (ABBREVIATED, "Abbreviated")
    ]

    # NPI (Numbering Plan Indicator) choices
    NPI_UNKNOWN = 0
    NPI_ISDN = 1
    NPI_DATA = 2
    NPI_TELEX = 3
    NPI_LAND_MOBILE = 4
    NPI_NATIONAL = 5
    NPI_PRIVATE = 6
    NPI_ERMES = 10
    NPI_INTERNET = 14
    NPI_WAP_CLIENT_ID = 18

    NPI_TYPES = [
        (NPI_UNKNOWN, "Unknown"),
        (NPI_ISDN, "ISDN"),
        (NPI_DATA, "Data"),
        (NPI_TELEX, "Telex"),
        (NPI_LAND_MOBILE, "Land Mobile"),
        (NPI_NATIONAL, "National"),
        (NPI_PRIVATE, "Private"),
        (NPI_ERMES, "Ermes"),
        (NPI_INTERNET, "Internet"),
        (NPI_WAP_CLIENT_ID, "WAP Client ID"),
    ]

    # Priority choices
    PRIORITY_0 = 0
    PRIORITY_1 = 1
    PRIORITY_2 = 2
    PRIORITY_3 = 3
    PRIORITY_CHOICES = [
        (PRIORITY_0, "0"),
        (PRIORITY_1, "1"),
        (PRIORITY_2, "2"),
        (PRIORITY_3, "3"),
    ]

    # Data coding choices
    SMSC_DEFAULT = 0
    IA5_ASCII = 1
    OCTET_UNSPECIFIED = 2
    LATIN1 = 3
    OCTET_UNSPECIFIED_COMMON = 4
    JIS = 5
    CYRILLIC = 6
    ISO_8859_8 = 7
    UCS2 = 8
    PICTOGRAM = 9
    ISO_2022_JP = 10
    EXTENDED_KANJI_JIS = 13
    KS_C_5601 = 14
    CODING_SCHEMES = [
        (SMSC_DEFAULT, "SMSC Default"),
        (IA5_ASCII, "IA5 ASCII"),
        (OCTET_UNSPECIFIED, "OCTET Unspecified"),
        (LATIN1, "Latin1"),
        (OCTET_UNSPECIFIED_COMMON, "OCTET Unspecified Common"),
        (JIS, "JIS"),
        (CYRILLIC, "Cyrilic"),
        (ISO_8859_8, "ISO-8859-8"),
        (UCS2, "UCS2"),
        (PICTOGRAM, "Pictogram"),
        (ISO_2022_JP, "ISO-2022-JP"),
        (EXTENDED_KANJI_JIS, "Extended Kanji Jis"),
        (KS_C_5601, "KS C 5601"),
    ]

    # Replace if present flag choices
    RIPF_DO_NOT_REPLACE = 0
    RIPF_REPLACE = 1
    RIPF_CHOICES = [
        (RIPF_DO_NOT_REPLACE, "Do not replace"),
        (RIPF_REPLACE, "Replace"),
    ]

    # DLR message ID bases choices
    DLR_MSG_ID_SAME_BASE = 0
    DLR_MSG_ID_HEX_TO_DEC = 1
    DLR_MSG_ID_DEC_TO_HEX = 2
    DLR_MSG_ID_BASES = [
        (DLR_MSG_ID_SAME_BASE, "Same base"),
        (DLR_MSG_ID_HEX_TO_DEC, "Hex to Decimal"),
        (DLR_MSG_ID_DEC_TO_HEX, "Decimal to Hex"),
    ]

    workspace = models.ForeignKey("workspace.WorkSpace", on_delete=models.CASCADE)
    host = models.CharField(
        max_length=50,
        help_text=_("Hostname or IP address of the SMSC"),
    )
    port = models.IntegerField(
        default=2775,
        help_text=_("The port number for the connection to the SMSC.")
    )
    username = models.CharField(
        max_length=15,  # Matches SMPPClientConfig limit
        default="smppclient",
        help_text="Username to connect to SMSC server"
    )
    password = models.CharField(
        max_length=16,  # Matches SMPPClientConfig limit
        help_text="Password to connect to SMSC server"
    )
    system_type = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="The system_type parameter categorizes the type of ESME"
    )
    log_file = models.TextField(
        null=True,
        blank=True,
        help_text=_("Log file path for this connector")
    )
    log_rotate = models.CharField(
        max_length=30,
        choices=LOG_ROTATE_CHOICES,
        default=MIDNIGHT,
        help_text=_("When to rotate the log file"),
    )
    log_level = models.IntegerField(
        default=logging.INFO,
        help_text="Logging level: 10=DEBUG, 20=INFO, 30=WARNING, 40=ERROR, 50=CRITICAL"
    )
    log_privacy = models.BooleanField(
        default=False,
        help_text="Don't log message content if enabled"
    )
    use_ssl = models.BooleanField(
        default=False,
        help_text="Activate SSL connection"
    )
    ssl_certificate_file = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Path to SSL certificate file"
    )
    bind_operation = models.CharField(
        max_length=100,
        choices=BIND_TYPES,
        default=TRANSCEIVER,
        help_text="Bind type: transceiver, receiver or transmitter",
    )
    session_init_timer_secs = models.IntegerField(
        default=30,
        help_text="Timeout for response to bind request (seconds)"
    )
    enquire_link_timer_secs = models.IntegerField(
        default=30,
        help_text="Enquire link interval (seconds)"
    )
    inactivity_timer_secs = models.IntegerField(
        default=300,
        help_text="Maximum time between transactions before reconnecting (seconds)"
    )
    response_timer_secs = models.IntegerField(
        default=120,
        help_text="Timeout for responses to any request PDU (seconds)"
    )
    pdu_read_timer_secs = models.IntegerField(
        default=10,
        help_text="Timeout for reading a single PDU (seconds)"
    )
    reconnect_on_connection_loss = models.BooleanField(
        default=True,
        help_text="Reconnect on connection loss"
    )
    reconnect_on_connection_failure = models.BooleanField(
        default=True,
        help_text="Reconnect on connection failure"
    )
    reconnect_on_connection_loss_delay = models.IntegerField(
        default=10,
        help_text="Reconnect delay on connection loss (seconds)"
    )
    reconnect_on_connection_failure_delay = models.IntegerField(
        default=10,
        help_text="Reconnect delay on connection failure (seconds)"
    )
    source_addr = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="Default source address for SMS-MT"
    )
    source_addr_ton = models.IntegerField(
        choices=TON_VALUES,
        default=NATIONAL,
        help_text="Source address TON"
    )
    source_addr_npi = models.IntegerField(
        choices=NPI_TYPES,
        default=NPI_ISDN,
        help_text="Source address NPI"
    )
    dest_addr_ton = models.IntegerField(
        choices=TON_VALUES,
        default=INTERNATIONAL,
        help_text="Destination address TON"
    )
    dest_addr_npi = models.IntegerField(
        choices=NPI_TYPES,
        default=NPI_ISDN,
        help_text="Destination address NPI"
    )
    address_ton = models.IntegerField(
        choices=TON_VALUES,
        default=UNKNOWN,
        help_text="Bind address TON"
    )
    address_npi = models.IntegerField(
        choices=NPI_TYPES,
        default=NPI_ISDN,
        help_text="Bind address NPI"
    )
    address_range = models.TextField(
        null=True,
        blank=True,
        help_text="Allowed MS addresses"
    )
    validity_period = models.IntegerField(
        null=True,
        blank=True,
        help_text="Default validity period for SMS-MT (seconds)"
    )
    priority_flag = models.IntegerField(
        choices=PRIORITY_CHOICES,
        default=PRIORITY_0,
        help_text="SMS-MT default priority"
    )
    registered_delivery = models.IntegerField(
        default=1,
        choices=[
            (1, "No SMSC Delivery Receipt Requested"),
            (2, "SMSC Delivery Receipt Requested"),
            (3, "SMSC Delivery Receipt Requested For Failure")
        ],
        help_text="Request SMSC delivery receipt"
    )
    replace_if_present_flag = models.IntegerField(
        choices=RIPF_CHOICES,
        default=RIPF_DO_NOT_REPLACE,
        help_text="Replace if present flag"
    )
    data_coding = models.IntegerField(
        choices=CODING_SCHEMES,
        default=SMSC_DEFAULT,
        help_text="Default message encoding"
    )
    sm_default_msg_id = models.IntegerField(
        default=0,
        help_text="SMSC index of pre-defined message"
    )
    dlr_expiry = models.IntegerField(
        default=86400,
        help_text="How long to wait for receipts (seconds)"
    )
    requeue_delay = models.IntegerField(
        default=120,
        help_text="Delay before retrying rejected messages (seconds)"
    )
    submit_sm_throughput = models.IntegerField(
        default=1,
        help_text="Message throttling in MPS (0 for unlimited)"
    )
    dlr_msg_id_bases = models.IntegerField(
        choices=DLR_MSG_ID_BASES,
        default=DLR_MSG_ID_SAME_BASE,
        help_text="How to handle message IDs in receipts"
    )

    def __str__(self):
        return str(self.cid)

    @property
    def cid(self):
        return f"smppc_{self.workspace.id}_{str(self.id)}"

    def save(self, *args, **kwargs):
        # manipulate the cid, to ensure we add workspace metadata
        run_on_reactor = kwargs.pop('run_on_reactor', True)
        super().save(*args, **kwargs)
        if run_on_reactor:
            self.jasmin_add_connector()

    def start(self):
        self.is_active = True
        self.save(run_on_reactor=False)
        self.jasmin_start_connector()

    def stop(self):
        self.is_active = False
        self.save(run_on_reactor=False)
        self.jasmin_stop_connector()

    def restart(self):
        self.stop()
        sleep(5)  # sleep a bit
        self.start()

    def delete(self, *args, **kwargs):
        run_on_reactor = kwargs.pop('run_on_reactor', True)
        if run_on_reactor:
            self.jasmin_remove_connector()
        else:
            super().delete(*args, **kwargs)

    class Meta:
        db_table = "jasmin_smpp_connector"

    def to_smpp_client_config(self) -> JCliSMPPClientConfig:
        """Convert Django model instance to SMPPClientConfig"""
        connector_id = f"smppc_{self.workspace.id}_{str(self.id)}"
        params = {
            'id': connector_id,
            'port': self.port,
            'host': self.host,
            'username': self.username,
            'password': self.password,
            'systemType': self.system_type,
            'log_file': self.log_file,
            'log_rotate': self.log_rotate,
            'log_level': self.log_level,
            'log_privacy': self.log_privacy,
            'sessionInitTimerSecs': self.session_init_timer_secs,
            'enquireLinkTimerSecs': self.enquire_link_timer_secs,
            'inactivityTimerSecs': self.inactivity_timer_secs,
            'responseTimerSecs': self.response_timer_secs,
            'pduReadTimerSecs': self.pdu_read_timer_secs,
            'dlr_expiry': self.dlr_expiry,
            'reconnectOnConnectionLoss': self.reconnect_on_connection_loss,
            'reconnectOnConnectionFailure': self.reconnect_on_connection_failure,
            'reconnectOnConnectionLossDelay': self.reconnect_on_connection_loss_delay,
            'reconnectOnConnectionFailureDelay': self.reconnect_on_connection_failure_delay,
            'useSSL': self.use_ssl,
            'SSLCertificateFile': self.ssl_certificate_file,
            'bindOperation': self.bind_operation,
            'source_addr': self.source_addr,
            'source_addr_ton': TON_VALUES[str(self.source_addr_ton)],
            'source_addr_npi': NPI_VALUES[str(self.source_addr_npi)],
            'dest_addr_ton': TON_VALUES[str(self.dest_addr_ton)],
            'dest_addr_npi': NPI_VALUES[str(self.dest_addr_npi)],
            'addressTon': TON_VALUES[str(self.address_ton)],
            'addressNpi': NPI_VALUES[str(self.address_npi)],
            'addressRange': self.address_range,
            'validity_period': self.validity_period,
            'priority_flag': PRIORITY_VALUES[str(self.priority_flag)],
            'registered_delivery': RegisteredDelivery(REGISTERED_DELIVERY_VALUES[str(self.registered_delivery)]),
            'replace_if_present_flag': REPLACE_IF_PRESENT_VALUES[str(self.replace_if_present_flag)],
            'data_coding': self.data_coding,
            'requeue_delay': self.requeue_delay,
            'submit_sm_throughput': self.submit_sm_throughput,
            'dlr_msg_id_bases': self.dlr_msg_id_bases,
        }
        if params["log_file"] is None:
            # if log file is not set leave it upto jasmin to default it
            del params['log_file']

        return JCliSMPPClientConfig(**params)

    def to_route_connector(self) -> Connector:
        return SmppClientConnector(self.cid)

    @classmethod
    def from_smpp_client_config(cls, config_data, workspace):
        """Create Django model instance from SMPPClientConfig dictionary"""
        connector = cls(
            workspace=workspace,
            cid=uuid.UUID(config_data['id']) if 'id' in config_data else uuid.uuid4(),
            host=config_data.get('host', '127.0.0.1'),
            port=config_data.get('port', 2775),
            username=config_data.get('username', 'smppclient'),
            password=config_data.get('password', 'password'),
            system_type=config_data.get('systemType', ''),
            log_file=config_data.get('log_file', None),
            log_rotate=config_data.get('log_rotate', 'midnight'),
            log_level=config_data.get('log_level', logging.INFO),
            log_privacy=config_data.get('log_privacy', False),
            session_init_timer_secs=config_data.get('sessionInitTimerSecs', 30),
            enquire_link_timer_secs=config_data.get('enquireLinkTimerSecs', 30),
            inactivity_timer_secs=config_data.get('inactivityTimerSecs', 300),
            response_timer_secs=config_data.get('responseTimerSecs', 120),
            pdu_read_timer_secs=config_data.get('pduReadTimerSecs', 10),
            dlr_expiry=config_data.get('dlr_expiry', 86400),
            reconnect_on_connection_loss=config_data.get('reconnectOnConnectionLoss', True),
            reconnect_on_connection_failure=config_data.get('reconnectOnConnectionFailure', True),
            reconnect_on_connection_loss_delay=config_data.get('reconnectOnConnectionLossDelay', 10),
            reconnect_on_connection_failure_delay=config_data.get('reconnectOnConnectionFailureDelay', 10),
            use_ssl=config_data.get('useSSL', False),
            ssl_certificate_file=config_data.get('SSLCertificateFile', None),
            bind_operation=config_data.get('bindOperation', 'transceiver'),
            source_addr=config_data.get('source_addr', None),
            source_addr_ton=config_data.get('source_addr_ton', cls.NATIONAL),
            source_addr_npi=config_data.get('source_addr_npi', cls.NPI_ISDN),
            dest_addr_ton=config_data.get('dest_addr_ton', cls.INTERNATIONAL),
            dest_addr_npi=config_data.get('dest_addr_npi', cls.NPI_ISDN),
            address_ton=config_data.get('addressTon', cls.UNKNOWN),
            address_npi=config_data.get('addressNpi', cls.NPI_ISDN),
            address_range=config_data.get('addressRange', None),
            validity_period=config_data.get('validity_period', None),
            priority_flag=config_data.get('priority_flag', cls.PRIORITY_0),
            registered_delivery=config_data.get('registered_delivery', False),
            replace_if_present_flag=config_data.get('replace_if_present_flag', cls.RIPF_DO_NOT_REPLACE),
            data_coding=config_data.get('data_coding', cls.SMSC_DEFAULT),
            requeue_delay=config_data.get('requeue_delay', 120),
            submit_sm_throughput=config_data.get('submit_sm_throughput', 1),
            dlr_msg_id_bases=config_data.get('dlr_msg_id_bases', cls.DLR_MSG_ID_SAME_BASE),
        )
        # TODO, hand over to django, let it try to pick if by cid from db then update any
        #  field that do not match or just create a new on, handle clever way to link the workspace


class JasminFilter(JasminBaseFilter, SmartModel):
    """
        Jasmin does not provide a PB for the filters as they are attached to an active session.
        Just persist the Router using it and it will be persisted too.

        Nonetheless, let us save them locally here in django, so we do not need to recreate them each time
    """
    filter_type = models.CharField(
        max_length=40,
        null=False
    )

    def save(self, *args, **kwargs):
        # validate the params given a filter  and params
        validated = None
        if self.nature == MO:
            validated = MoFilters.validate(self.filter_type, self.param.get("value"))
        elif self.nature == MT:
            validated = MTFilters.validate(self.filter_type, self.param.get("value"))
        else:
            if self.param and isinstance(self.param, dict):
                validated = AllFilters.validate(self.filter_type, self.param.get("value"))
        if validated:
            self.param["value"] = validated
        super(JasminFilter, self).save(*args, **kwargs)

    def to_jasmin_filter(self):
        if self.filter_type == MO:
            jasmin_filter = MoFilters[self.filter_type].value[0]
        elif self.filter_type == MT:
            jasmin_filter = MTFilters[self.filter_type].value[0]
        else:
            jasmin_filter = AllFilters[self.filter_type].value[0]
        if self.param and isinstance(self.param, dict):
            payload = {self.param["key"]: self.param["value"]}
            return jasmin_filter(**payload)

        return jasmin_filter()

    class Meta:
        db_table = 'jasmin_filter'


class JasminRoute(BaseJasminModel, JasminBaseRouter, SmartModel):
    router_type = models.CharField(
        max_length=25,
        choices=MTRouterChoices,
        default=MTRouterChoices.DefaultRoute)

    filters = models.ManyToManyField(JasminFilter, related_name="mt_routers")
    connectors = models.ManyToManyField(JasminSMPPConnector, related_name="routers")

    def to_jasmin_route(self):

        if self.nature == "MT":
            JasminMTRoute = MTRouter.jasmin_router_class(self.router_type)
            filters = [f.to_jasmin_filter() for f in self.filters.all()]
            connectors = [c.to_route_connector() for c in self.connectors.all()]
            self.rate = float(self.rate)
            if len(connectors) == 0:
                raise Exception("Could not proceed saving MT router because No connectors found")
            connector = connectors[0]

            if JasminMTRoute == DefaultRoute:
                route = DefaultRoute(connector=connector, rate=self.rate)
            elif JasminMTRoute == StaticMTRoute:
                route = StaticMTRoute(connector=connector, filters=filters, rate=self.rate)
            elif JasminMTRoute == RandomRoundrobinMTRoute:
                # multiple filters and multiple connectors
                route = RandomRoundrobinMTRoute(filters=filters, connectors=connectors, rate=self.rate)
            else:
                route = FailoverMTRoute(filters=filters, connectors=connectors, rate=self.rate)
            return route
        else:
            JasminMORoute = MORouter.jasmin_router_class(self.router_type)
            filters = [f.to_jasmin_filter() for f in self.filters.all()]
            connectors = [c.to_route_connector() for c in self.connectors.all()]

            if len(connectors) == 0:
                raise Exception("Could not proceed saving MT router because No connectors found")
            connector = connectors[0]
            if JasminMORoute is DefaultRoute:
                route = DefaultRoute(connector=connector, rate=self.rate)
            elif JasminMORoute is StaticMORoute:
                route = StaticMORoute(connector=connector, filters=filters)
            elif JasminMORoute is RandomRoundrobinMORoute:
                # multiple filters and multiple connectors
                route = RandomRoundrobinMORoute(filters=filters, connectors=connectors)
            else:
                route = FailoverMORoute(filters=filters, connectors=connectors)
            return route

    def save(self, *args, **kwargs):
        run_on_reactor = kwargs.pop('run_on_reactor', True)
        super().save(*args, **kwargs)
        if run_on_reactor:
            self.jasmin_add_route()

    def delete(self, *args, **kwargs):
        run_on_reactor = kwargs.pop('run_on_reactor', True)
        if run_on_reactor:
            self.jasmin_remove_route()
        else:
            super().delete(*args, **kwargs)

    class Meta:
        db_table = 'jasmin_route'

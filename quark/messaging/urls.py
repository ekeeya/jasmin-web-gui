from django.urls import path, re_path

from quark.messaging.views import (
    BalanceRateView,
    BulkSendSMSView,
    OutboundMessageCRUDL,
    SendSMSView,
    SetConsoleModeView,
)

urlpatterns = [
    path("console/mode/", SetConsoleModeView.as_view(), name="messaging.console_mode"),
    path("messaging/send/", SendSMSView.as_view(), name="messaging.send"),
    path("messaging/bulk/", BulkSendSMSView.as_view(), name="messaging.bulk_send"),
    path("messaging/balance/", BalanceRateView.as_view(), name="messaging.balance"),
]

urlpatterns += OutboundMessageCRUDL().as_urlpatterns()

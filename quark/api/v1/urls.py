from django.urls import path, re_path
from rest_framework.urlpatterns import format_suffix_patterns

from quark.api.v1.messaging import MessagingSendAPIView

urlpatterns = [
    path("messaging/send/", MessagingSendAPIView.as_view(), name="api.v1.messaging_send"),
]

urlpatterns = format_suffix_patterns(urlpatterns, allowed=["json"])

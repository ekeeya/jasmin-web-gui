from django.urls import re_path
from rest_framework.urlpatterns import format_suffix_patterns

from .views import ServiceEndpoint

urlpatterns = [
    re_path(r"^services$", ServiceEndpoint.as_view(), name="api.v1.services"),
]

urlpatterns = format_suffix_patterns(urlpatterns, allowed=["json"])
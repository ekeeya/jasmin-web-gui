from django.conf.urls import include
from django.urls import re_path

urlpatterns = [
    re_path(r"^api/v1/", include("umoja.api.v1.urls")),
]

from django.urls import re_path
from rest_framework.urlpatterns import format_suffix_patterns


urlpatterns = [

]

urlpatterns = format_suffix_patterns(urlpatterns, allowed=["json"])
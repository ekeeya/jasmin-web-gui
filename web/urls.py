from .views import SMSCallback
from django.urls import path

urlpatterns = [
    path("dlr", SMSCallback.as_view(), name="dlr"),
]

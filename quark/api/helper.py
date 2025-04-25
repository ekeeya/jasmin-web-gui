import logging

from django.conf import settings
from django.contrib.auth.models import User
from django.http import HttpResponseServerError
from rest_framework import status
from rest_framework.authentication import SessionAuthentication, BasicAuthentication
from rest_framework.exceptions import APIException, AuthenticationFailed
from rest_framework.pagination import CursorPagination

# from quark.workspace.models import User
from quark.utils.utils import str_to_bool

logger = logging.getLogger(__name__)


class APISessionAuthentication(SessionAuthentication):
    """
    Session authentication as used by the editor, explorer
    """


class APIBasicAuthentication(BasicAuthentication):
    """
        Basic authentication using username and password.
        Credentials: username:password

        DRF uses the User object from django.auth.models, but we have out custom User
    """

    def authenticate_credentials(self, userid, password, request=None):
        try:
            super(APIBasicAuthentication, self).authenticate_credentials(userid, password, request)
            user = User.objects.get(username__exact=userid)
            return user, None
        except User.DoesNotExist:
            raise AuthenticationFailed('Wrong credentials')

        except Exception as e:
            raise AuthenticationFailed("Wrong credentials")


class InvalidQueryError(APIException):
    """
    Exception class for invalid queries in list endpoints
    """

    status_code = status.HTTP_400_BAD_REQUEST


def api_exception_handler(exc, context):
    """
    Custom exception handler which prevents responding to API requests that error with an HTML error page
    """
    from rest_framework.views import exception_handler

    response = exception_handler(exc, context)

    if response or not getattr(settings, "REST_HANDLE_EXCEPTIONS", False):
        return response
    else:
        # ensure exception still goes to Sentry
        logger.error("Exception in API request: %s" % str(exc), exc_info=True)

        # respond with simple message
        return HttpResponseServerError("Server Error. Site administrators have been notified.")


class CreatedOnCursorPagination(CursorPagination):
    ordering = ("-created_on", "-id")
    offset_cutoff = 100000


class ModifiedOnCursorPagination(CursorPagination):
    ordering = ("-modified_on", "-id")
    offset_cutoff = 100000

    def get_ordering(self, request, queryset, view):
        if str_to_bool(request.GET.get("reverse")):
            return "modified_on", "id"
        else:
            return self.ordering

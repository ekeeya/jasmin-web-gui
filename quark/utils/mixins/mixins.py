import logging

from django.db import transaction
from django.http import HttpResponse

logger = logging.getLogger(__name__)


class NonAtomicMixin:
    """
        Mixin to disable automatic transaction wrapping of a class based view
    """

    @transaction.non_atomic_requests
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)


class PostOnlyMixin:
    """Mixin to make a class based view be POST only"""

    def get(self, *args, **kwargs):
        return HttpResponse("Only Method PST is allowed", status=405)


class RequireAuthMixin:
    """Mixin to redirect the user to login page if they haven't authenticated."""

    recent_auth_seconds = 10*60
    recent_auth_includes_formax = False

    def pre_process(self, request, *args, **kwargs):
        # TODO we shall complete it
        pass


class SystemOnlyMixin:
    """Mixin to ensure the view is only accessed by system users"""

    def has_permission(self, request, *args, **kwargs):
        return self.request.user.is_staff or request.user.is_superuser

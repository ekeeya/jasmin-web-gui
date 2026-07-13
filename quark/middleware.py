import traceback

from django.conf import settings
from django.contrib import messages
from django.http import HttpResponseForbidden, HttpResponseRedirect
from django.urls import reverse
from django.utils import timezone

from quark.workspace.models import WorkSpace, User


class ExceptionMiddleware:
    def __init__(self, get_response=None):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_exception(self, request, exception):
        if settings.DEBUG:
            traceback.print_exc()

        return None


class WorkspaceMiddleware:
    """
    Determines the workspace for this request and sets it on the request.
    """

    session_key = "workspace_id"
    header_name = "X-Joyce-Workspace"
    service_header_name = "X-Joyce-Service-Workspace"
    select_related = ("created_by",)

    def __init__(self, get_response=None):
        self.get_response = get_response

    def __call__(self, request):
        assert hasattr(request, "user"), "must be called after django.contrib.auth.middleware.AuthenticationMiddleware"

        request.workspace = self.determine_workspace(request)

        # if request has an workspace header, ensure it matches the current workspace (used to prevent
        # cross-workspace form submissions)
        posted_workspace_id = request.headers.get(self.header_name)
        if posted_workspace_id and request.workspace and request.workspace.id != int(posted_workspace_id):
            return HttpResponseForbidden()

        # continue the chain, which in the case of the API will set request.workspace
        response = self.get_response(request)

        if request.workspace:
            # set a response header to make it easier to find the current workspace id
            response[self.header_name] = request.workspace.id

        return response

    def determine_workspace(self, request):
        user = request.user

        if not user.is_authenticated:
            return None

        # check for value in session
        workspace_id = request.session.get(self.session_key, None)

        # staff users alternatively can pass a service header
        if user.is_staff:
            workspace_id = request.headers.get(self.service_header_name, workspace_id)

        if workspace_id:
            workspace = (WorkSpace.objects.filter(is_active=True, id=workspace_id)
                         .select_related(*self.select_related).first())

            # only use if user actually belongs to this workspace
            if workspace and (user.is_staff or workspace.has_user(user)):
                return workspace

        # otherwise if user only belongs to one workspace, we can use that
        user_workspaces = User.get_workspaces_for_request(request)
        if user_workspaces.count() == 1:
            return user_workspaces[0]

        return None


class JasminConnectionGateMiddleware:
    """
    Force workspaces that have not chosen demo/custom Jasmin onto the workspace
    settings page until they are ready.
    """

    ALLOW_PREFIXES = (
        "/static/",
        "/media/",
        "/admin/",
        "/login/",
        "/users/logout/",
        "/workspace/settings/",
        "/workspace/signup/",
        "/api/",
        "/dlr",
        "/batch-callback",
    )

    def __init__(self, get_response=None):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        workspace = getattr(request, "workspace", None)
        if not user or not user.is_authenticated or not workspace:
            return self.get_response(request)

        if workspace.is_jasmin_ready():
            return self.get_response(request)

        path = request.path or "/"
        if path == "/" or any(path.startswith(p) for p in self.ALLOW_PREFIXES):
            return self.get_response(request)

        settings_url = reverse("workspace.workspace_settings")
        if path.rstrip("/") == settings_url.rstrip("/"):
            return self.get_response(request)

        messages.info(
            request,
            "Choose Local demo Jasmin or connect your own Jasmin before using the console.",
        )
        return HttpResponseRedirect(settings_url)


class TimezoneMiddleware:
    """
    Activates the timezone for the current workspace
    """

    def __init__(self, get_response=None):
        self.get_response = get_response

    def __call__(self, request):
        assert hasattr(request, "workspace"), "must be called after quark.middleware.WorkspaceMiddleware"

        if request.workspace:
            timezone.activate(request.workspace.timezone)
        else:
            timezone.activate(settings.USER_TIME_ZONE)

        return self.get_response(request)

#  Copyright (c) 2025
#  File created on 2025/4/25
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
from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from smartmin.mixins import NonAtomicMixin
from smartmin.users.models import FailedLogin
from smartmin.views import SmartCRUDL, SmartCreateView, SmartUpdateView
from django.contrib.auth.views import LoginView as AuthLoginView

from quark.messaging.api_docs_pdf import build_messaging_api_pdf
from quark.workspace.models import WorkSpace, User
from quark.workspace.views.forms import SignupForm, WorkspaceSettingsForm
from quark.workspace.views.mixins import WorkspacePermsMixin


def switch_to_workspace(request, workspace: WorkSpace):
    request.session["workspace_id"] = workspace.id if workspace else None


class LoginView(AuthLoginView):
    """
    Overrides the auth login view to add support for tracking failed logins.
    """

    template_name = "workspace/login/login.html"
    redirect_authenticated_user = True
    redirect_next_page = True

    def post(self, request, *args, **kwargs):
        form = self.get_form()

        form_is_valid = form.is_valid()  # clean form data

        lockout_timeout = getattr(settings, "USER_LOCKOUT_TIMEOUT", 10)
        failed_login_limit = getattr(settings, "USER_FAILED_LOGIN_LIMIT", 5)

        username = self.get_username(form)
        if not username:
            return self.form_invalid(form)

        user = User.objects.filter(username__iexact=username).first()
        valid_password = False

        # this could be a valid login by a user
        if user:
            # incorrect password?  create a failed login token
            valid_password = user.check_password(form.cleaned_data.get("password") or "")

        if not user or not valid_password:
            FailedLogin.objects.create(username=username)

        failures = FailedLogin.objects.filter(username__iexact=username)

        # if the failures reset after a period of time, then limit our query to that interval
        if lockout_timeout > 0:
            bad_interval = timezone.now() - timedelta(minutes=lockout_timeout)
            failures = failures.filter(failed_on__gt=bad_interval)

        # if there are too many failed logins, take them to the failed page
        if failures.count() >= failed_login_limit:
            # Correct password still clears the lockout so a legitimate user
            # is not stuck after a burst of bad attempts (e.g. forgotten pwd).
            if user and valid_password and form_is_valid:
                FailedLogin.objects.filter(username__iexact=username).delete()
                return self.form_valid(form)

            logout(request)
            minutes = lockout_timeout if lockout_timeout > 0 else 10
            messages.error(
                request,
                f"Too many failed sign-in attempts. Try again in about {minutes} minutes, "
                f"or ask an admin to clear the lockout.",
            )
            return HttpResponseRedirect(reverse("workspace.login"))

        # pass through the normal login process
        if form_is_valid:
            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    def form_valid(self, form):
        user = form.get_user()

        # user.record_auth()

        # clean up any failed logins for this username
        FailedLogin.objects.filter(username__iexact=self.get_username(form)).delete()

        return super().form_valid(form)

    def get_username(self, form):
        return form.cleaned_data.get("username")

    def get_success_url(self):
        return reverse("dashboard.dashboard_home")


class LogoutView(View):
    """
    Logouts user on a POST and redirects to the login page.
    """

    @csrf_exempt
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        logout(request)

        return HttpResponseRedirect(reverse("workspace.login"))


class WorkspaceCRUDL(SmartCRUDL):
    model = WorkSpace

    actions = ("signup", "create", "list", "settings",)

    class Signup(NonAtomicMixin, SmartCreateView):
        title = "Register Workspace"
        form_class = SignupForm
        permission = None

        def get_success_url(self):
            return reverse("workspace.workspace_settings")

        def save(self, obj):
            new_user = User.create(
                self.form.cleaned_data["username"],
                self.form.cleaned_data["email"],
                self.form.cleaned_data["first_name"],
                self.form.cleaned_data["last_name"],
                self.form.cleaned_data["password"]
            )

            workspace = WorkSpace.create(
                new_user,
                self.form.cleaned_data["country"],
                self.form.cleaned_data["name"],
                self.form.cleaned_data["timezone"],
            )

            switch_to_workspace(self.request, workspace)
            login(self.request, new_user)  # log the user in
            return workspace

    class Settings(WorkspacePermsMixin, SmartUpdateView):
        permission = "workspace.workspace_update"
        form_class = WorkspaceSettingsForm
        template_name = "workspace/settings.html"
        title = "Workspace settings"
        success_message = "Workspace settings saved."
        fields = (
            "jasmin_link",
            "jasmin_router_pb_host",
            "jasmin_router_pb_port",
            "jasmin_router_pb_username",
            "jasmin_router_pb_password",
            "jasmin_smpp_pb_host",
            "jasmin_smpp_pb_port",
            "jasmin_smpp_pb_username",
            "jasmin_smpp_pb_password",
            "jasmin_http_api_url",
            "jasmin_rest_api_url",
            "jasmin_user_sync_interval_mins",
            "messaging_api_enabled",
            "external_dlr_url",
            "external_dlr_method",
            "external_dlr_retry_delay_secs",
            "external_dlr_max_retries",
        )

        @classmethod
        def derive_url_pattern(cls, path, action):
            return r"^workspace/settings/$"

        def get_object(self, queryset=None):
            return self.derive_workspace()

        def get_success_url(self):
            return reverse("workspace.workspace_settings")

        def get_context_data(self, **kwargs):
            context = super().get_context_data(**kwargs)
            workspace = self.derive_workspace()
            context["workspace"] = workspace
            context["last_synced_at"] = workspace.jasmin_user_last_synced_at
            context["connection_tested_at"] = workspace.jasmin_connection_tested_at
            context["config_imported_at"] = workspace.jasmin_config_last_imported_at
            context["jasmin_ready"] = workspace.is_jasmin_ready() if workspace else False
            context["setup_mode"] = not context["jasmin_ready"]
            context["credentials_key_configured"] = bool(
                getattr(settings, "JOYCE_CREDENTIALS_KEY", "")
            )
            context["messaging_api_token"] = workspace.messaging_api_token or ""
            context["messaging_api_send_url"] = self.request.build_absolute_uri(
                reverse("api.v1.messaging_send")
            )
            context["messaging_api_docs_url"] = reverse(
                "workspace.messaging_api_docs_pdf"
            )
            return context

        def post(self, request, *args, **kwargs):
            action = request.POST.get("action") or request.POST.get("settings_action")
            if action == "test_connection":
                return self.test_connection(request)
            if action == "import_from_jasmin":
                return self.import_from_jasmin(request)
            if action == "clear_jasmin_connection":
                return self.clear_jasmin_connection(request)
            if action == "regenerate_messaging_api_token":
                return self.regenerate_messaging_api_token(request)
            return super().post(request, *args, **kwargs)

        def regenerate_messaging_api_token(self, request):
            import secrets

            workspace = self.derive_workspace()
            want_enabled = request.POST.get("messaging_api_enabled") in (
                "on",
                "true",
                "1",
                "True",
            )
            if not workspace.messaging_api_enabled and not want_enabled:
                return JsonResponse(
                    {
                        "ok": False,
                        "message": "Check Enable Joyce messaging API first, then refresh or save.",
                    },
                    status=400,
                )
            token = secrets.token_urlsafe(32)
            workspace.messaging_api_enabled = True
            workspace.messaging_api_token = token
            workspace.save(
                update_fields=["messaging_api_enabled", "messaging_api_token", "modified_on"]
            )
            return JsonResponse(
                {
                    "ok": True,
                    "message": "Token refreshed.",
                    "token": token,
                }
            )

        def _connection_from_request(self, request, workspace):
            """Build a JasminConnection from posted settings or saved workspace fields."""
            from quark.jasmin.connection import JasminConnection, JasminEndpoint, _demo_connection
            from quark.utils.crypto import decrypt_secret, looks_encrypted

            link = request.POST.get("jasmin_link") or workspace.jasmin_link or WorkSpace.JASMIN_LINK_DEMO
            if link != WorkSpace.JASMIN_LINK_CUSTOM:
                return _demo_connection(), link

            router_password = request.POST.get("jasmin_router_pb_password") or ""
            if not router_password:
                router_password = decrypt_secret(workspace.jasmin_router_pb_password)
            elif looks_encrypted(router_password):
                router_password = decrypt_secret(router_password)

            smpp_password = request.POST.get("jasmin_smpp_pb_password") or ""
            if not smpp_password:
                smpp_password = decrypt_secret(workspace.jasmin_smpp_pb_password)
            elif looks_encrypted(smpp_password):
                smpp_password = decrypt_secret(smpp_password)

            connection = JasminConnection(
                router_pb=JasminEndpoint(
                    host=request.POST.get("jasmin_router_pb_host") or workspace.jasmin_router_pb_host,
                    port=int(
                        request.POST.get("jasmin_router_pb_port")
                        or workspace.jasmin_router_pb_port
                        or 0
                    ),
                    username=(
                        request.POST.get("jasmin_router_pb_username")
                        or workspace.jasmin_router_pb_username
                    ),
                    password=router_password,
                ),
                smpp_pb=JasminEndpoint(
                    host=request.POST.get("jasmin_smpp_pb_host") or workspace.jasmin_smpp_pb_host,
                    port=int(
                        request.POST.get("jasmin_smpp_pb_port")
                        or workspace.jasmin_smpp_pb_port
                        or 0
                    ),
                    username=(
                        request.POST.get("jasmin_smpp_pb_username")
                        or workspace.jasmin_smpp_pb_username
                    ),
                    password=smpp_password,
                ),
                http_api_url=(
                    request.POST.get("jasmin_http_api_url")
                    or workspace.jasmin_http_api_url
                    or ""
                ).rstrip("/"),
                source="custom",
            )
            return connection, link

        def test_connection(self, request):
            """AJAX: verify Router PB and SMPP Client Manager PB are reachable."""
            from quark.jasmin.reactor import run_in_reactor
            from quark.jasmin.router_pb import RouterPBInterface
            from quark.jasmin.smpp_pb import SmppPBAdapter

            self.object = self.get_object()
            workspace = self.object

            try:
                connection, _link = self._connection_from_request(request, workspace)
            except Exception as exc:
                return JsonResponse({"ok": False, "message": str(exc)}, status=400)

            parts = []
            errors = []

            try:
                groups = run_in_reactor(RouterPBInterface(connection).get_all_groups) or []
                parts.append(f"Router PB OK ({len(groups)} group(s))")
            except Exception as exc:
                errors.append(f"Router PB: {exc}")

            try:
                connectors = run_in_reactor(SmppPBAdapter(connection).list_connectors) or []
                parts.append(f"SMPP PB OK ({len(connectors)} connector(s))")
            except Exception as exc:
                errors.append(f"SMPP PB: {exc}")

            if errors:
                detail = "; ".join(parts + errors) if parts else "; ".join(errors)
                return JsonResponse({"ok": False, "message": detail}, status=400)

            workspace.jasmin_connection_tested_at = timezone.now()
            workspace.save(update_fields=["jasmin_connection_tested_at", "modified_on"])
            return JsonResponse({
                "ok": True,
                "message": "; ".join(parts),
                "tested_at": workspace.jasmin_connection_tested_at.isoformat(),
            })

        def import_from_jasmin(self, request):
            """AJAX: pull groups/users/connectors/routes/filters/interceptors into Django."""
            from quark.jasmin.import_config import import_workspace_config

            self.object = self.get_object()
            workspace = self.object

            try:
                connection, _link = self._connection_from_request(request, workspace)
                stats = import_workspace_config(workspace, connection, user=request.user)
                workspace.refresh_from_db(fields=["jasmin_config_last_imported_at"])
                return JsonResponse({
                    "ok": True,
                    "message": stats.summary_message(),
                    "stats": stats.as_dict(),
                    "imported_at": (
                        workspace.jasmin_config_last_imported_at.isoformat()
                        if workspace.jasmin_config_last_imported_at
                        else None
                    ),
                })
            except Exception as exc:
                return JsonResponse({"ok": False, "message": str(exc)}, status=400)

        def clear_jasmin_connection(self, request):
            """Clear custom Jasmin fields and switch the workspace to Local demo Jasmin."""
            self.object = self.get_object()
            workspace = self.object
            workspace.jasmin_link = WorkSpace.JASMIN_LINK_DEMO
            workspace.clear_jasmin_custom_connection(save=False)
            workspace.save()
            messages.success(
                request,
                "Custom Jasmin connection cleared. Workspace is on Local demo Jasmin.",
            )
            return HttpResponseRedirect(self.get_success_url())


class MessagingAPIDocsPDFView(LoginRequiredMixin, WorkspacePermsMixin, View):
    """Download PDF documentation for Joyce's external messaging API."""

    permission = "workspace.workspace_update"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not self.has_permission(request, *args, **kwargs):
            raise PermissionDenied()
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        workspace = self.derive_workspace()
        if not workspace or not workspace.messaging_api_enabled:
            raise PermissionDenied(
                "Enable the Joyce messaging API in workspace settings to download docs."
            )
        send_url = request.build_absolute_uri(reverse("api.v1.messaging_send"))
        pdf_bytes = build_messaging_api_pdf(
            send_url=send_url,
            workspace_name=workspace.name or "",
        )
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = (
            'attachment; filename="joyce-messaging-api.pdf"'
        )
        return response

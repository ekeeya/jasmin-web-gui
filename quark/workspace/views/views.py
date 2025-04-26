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
from django.contrib.auth import login, logout
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from smartmin.mixins import NonAtomicMixin
from smartmin.users.models import FailedLogin
from smartmin.views import SmartCRUDL, SmartCreateView
from django.contrib.auth.views import LoginView as AuthLoginView

from quark.workspace.models import WorkSpace, User
from quark.workspace.views.forms import SignupForm


def switch_to_workspace(request, workspace: WorkSpace):
    request.session["workspace_id"] = workspace.id if workspace else None


class LoginView(AuthLoginView):
    """
    Overrides the auth login view to add support for tracking failed logins.
    """

    template_name = "workspace/login/login.html"
    redirect_authenticated_user = True

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
            valid_password = user.check_password(form.cleaned_data.get("password"))

        if not user or not valid_password:
            FailedLogin.objects.create(username=username)

        failures = FailedLogin.objects.filter(username__iexact=username)

        # if the failures reset after a period of time, then limit our query to that interval
        if lockout_timeout > 0:
            bad_interval = timezone.now() - timedelta(minutes=lockout_timeout)
            failures = failures.filter(failed_on__gt=bad_interval)

        # if there are too many failed logins, take them to the failed page
        if len(failures) >= failed_login_limit:
            logout(request)
            return HttpResponseRedirect(reverse("workspace.login"))

        # pass through the normal login process
        if form_is_valid:
            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    def form_valid(self, form):
        user = form.get_user()

        user.record_auth()

        # clean up any failed logins for this username
        FailedLogin.objects.filter(username__iexact=self.get_username(form)).delete()

        return super().form_valid(form)

    def get_username(self, form):
        return form.cleaned_data.get("username")


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

    actions = ("signup", "create", "list",)

    class Signup(NonAtomicMixin, SmartCreateView):
        title = "Register Workspace"
        form_class = SignupForm
        permission = None

        def get_success_url(self):
            return "/"

        def save(self, obj):
            new_user = User.create(
                self.form.cleaned_data["username"],
                self.form.cleaned_data["email"],
                self.form.cleaned_data["first_name"],
                self.form.cleaned_data["last_name"],
                self.form.cleaned_data["password"]
            )

            WorkSpace.create(new_user,
                             self.form.cleaned_data["country"],
                             self.form.cleaned_data["name"],
                             self.form.cleaned_data["timezone"])

            switch_to_workspace(self.request, obj)
            login(self.request, new_user)  # log the user in
            return obj

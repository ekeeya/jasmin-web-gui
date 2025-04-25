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
from django.contrib.auth import login
from smartmin.mixins import NonAtomicMixin
from smartmin.views import SmartCRUDL, SmartCreateView

from quark.workspace.models import WorkSpace, User
from quark.workspace.views.forms import SignupForm


def switch_to_workspace(request, workspace:WorkSpace):
    request.session["workspace_id"] = workspace.id if workspace else None


class WorkSpaceCRUDL(SmartCRUDL):
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

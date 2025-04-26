#  Copyright (c) 2025
#  File created on 2025/4/26
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
from django.urls import reverse
from smartmin.mixins import NonAtomicMixin
from smartmin.views import SmartCRUDL, SmartCreateView

from quark.jasmin.models import JasminGroup
from quark.jasmin.views.forms import JasminGroupForm
from quark.workspace.views.mixins import WorkspacePermsMixin


class JasminGroupCRUDL(SmartCRUDL):
    model = JasminGroup
    actions = ("create", "list", "update", "delete",)

    class Create(WorkspacePermsMixin, NonAtomicMixin, SmartCreateView):
        title = "New Jasmin Group"
        form_class = JasminGroupForm
        permission = "jasmin.jasmingroup_create"
        template_name = "jasmin/group_create.html"

        def get_form_kwargs(self):
            kwargs = super().get_form_kwargs()
            kwargs["workspace"] = self.derive_workspace()
            return kwargs

        def form_valid(self, form):
            self.object = JasminGroup.create(
                form.cleaned_data["gid"],
                form.cleaned_data["workspace"],
                form.cleaned_data["description"],
            )

            response = self.render_to_response(
                self.get_context_data(
                    form=form,
                    success_url=self.get_success_url(),
                )
            )
            return response

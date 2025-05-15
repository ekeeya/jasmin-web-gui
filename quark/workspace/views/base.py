#  Copyright (c) 2025
#  File created on 2025/4/27
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
from smartmin.views import SmartListView

from quark.jasmin.models import JasminUser
from quark.workspace.views.mixins import WorkspacePermsMixin


class BaseListView(WorkspacePermsMixin, SmartListView):
    """
        Filter list records that belong to a given workspace
    """
    add_button = True

    def derive_queryset(self, **kwargs):
        # for jasmin users workspace is got from group
        if self.model == JasminUser:
            return super().derive_queryset(**kwargs).filter(group__workspace=self.request.workspace)
        return super().derive_queryset(**kwargs).filter(workspace=self.request.workspace)

    def build_actions(self):
        pass

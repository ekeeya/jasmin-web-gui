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




class WorkspacePermsMixin:
    """
    Mixin for views that require workspace permissions. `has_permission` will be called to determine if the current view is
    accessible to the current user. `has_workspace_perm` can be called when rendering the view to determine what other content
    is also accessible to the user.
    """

    def derive_workspace(self):
        return self.request.workspace

    def has_workspace_perm(self, permission: str) -> bool:
        """
        Figures out if the current user has the given permission.
        """

        workspace = self.derive_workspace()
        user = self.request.user

        # can't have a workspace perm without a workspace
        if not workspace:
            return False

        if user.is_anonymous:
            return False

        return user.is_staff or user.has_workspace_perm(workspace, permission)

    def has_permission(self, request, *args, **kwargs) -> bool:
        """
        Figures out if the current user has the required permission for this view.
        """

        self.kwargs = kwargs
        self.args = args
        self.request = request

        return self.has_workspace_perm(self.permission)

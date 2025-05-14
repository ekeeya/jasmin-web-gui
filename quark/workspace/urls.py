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


from django.urls import re_path

from .views import (
    WorkspaceCRUDL,
    LoginView,
    LogoutView
)

urlpatterns = WorkspaceCRUDL().as_urlpatterns()

urlpatterns += [
    re_path(r"^login/$", LoginView.as_view(), name="workspace.login"),
    re_path(r"^users/logout/$", LogoutView.as_view(), name="users.user_logout"),
]
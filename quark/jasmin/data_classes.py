#
#  Copyright (c) 2024
#  File created on 2024/7/20
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

from dataclasses import dataclass
from jasmin.routing.jasminApi import Group


@dataclass
class JasminUserConfig:
    username: str
    password: str
    group: Group
    uid: str

    def __init__(self, username: str, password: str, gid: str):
        self.username = username
        self.password = password
        self.group = Group(gid)
        self.uid = username

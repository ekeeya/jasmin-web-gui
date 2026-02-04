#
#  Copyright (c) 2024
#  File created on 2024/7/17
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
import os

JASMIN_HOST = os.getenv("JASMIN_HOST", "127.0.0.1")
JASMIN_PORT = os.getenv("JASMIN_PORT", "8990")
JASMIN_JCLI_USERNAME = os.getenv("JASMIN_JCLI_USERNAME", "jcliadmin")  # jcliadmin if authentication=True in your jasmin.cfg
JASMIN_JCLI_PASSWORD = os.getenv("JASMIN_JCLI_PASSWORD", "jclipwd")  # jclipwd

JASMIN_ROUTER_PB_HOST = os.getenv("JASMIN_ROUTER_PB_HOST", "127.0.0.1")
JASMIN_ROUTER_PB_PORT = int(os.getenv("JASMIN_ROUTER_PB_PORT", "8988"))
JASMIN_ROUTER_PB_USERNAME = os.getenv("JASMIN_ROUTER_PB_USERNAME", "radmin")
JASMIN_ROUTER_PB_PASSWORD = os.getenv("JASMIN_ROUTER_PB_PASSWORD", "rpwd")

JASMIN_SMPP_PB_HOST = os.getenv("JASMIN_SMPP_PB_HOST", "127.0.0.1")
JASMIN_SMPP_PB_PORT = int(os.getenv("JASMIN_SMPP_PB_PORT", "8989"))
JASMIN_SMPP_PB_USERNAME = os.getenv("JASMIN_SMPP_PB_USERNAME", "cmadmin")
JASMIN_SMPP_PB_PASSWORD = os.getenv("JASMIN_SMPP_PB_PASSWORD", "cmpwd")

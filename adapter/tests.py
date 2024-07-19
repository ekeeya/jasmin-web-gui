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
import uuid
import random
from twisted.internet.defer import Deferred
from twisted.internet import reactor, defer
from jasmin.routing.jasminApi import User, Group
from django.test import TestCase
from django.contrib.auth.models import User
from adapter.router_pb import RouterPBInterface
from quark.utils import logger, to_dict
from .serializers import JasminUserSerializer
from .models import JasminGroup
import json


class JasminAdapterTestCase(TestCase):
    router_pb_interface = None

    def setUp(self):
        self.router_pb_interface = RouterPBInterface()
        self.user = User.objects.create_user(username='testuser', password='12345678')

    def test_jasmin_interface(self):
        @defer.inlineCallbacks
        def workflow():
            try:
                yield self.router_pb_interface.connect()
                yield self.router_pb_interface.add_group('test_group', False)
                g1 = Group("test")
                yield self.router_pb_interface.add_user('test_user', 'password', g1, False)
                users = yield self.router_pb_interface.get_all_users()
                groups = yield self.router_pb_interface.get_all_groups()
                self.router_pb_interface.close()
                self.assertIsInstance(users, list)
                self.assertIsInstance(groups, list)
            except Exception as e:
                logger.error(e)
                self.router_pb_interface.close()

        self.router_pb_interface.execute(workflow)

    def test_db_jasmin_group_creation(self):
        self.client.login(username='testuser', password='12345678')
        group = JasminGroup.create("db_test_group")
        self.assertIsInstance(group, JasminGroup)

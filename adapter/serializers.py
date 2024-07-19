#
#  Copyright (c) 2024
#  File created on 2024/7/18
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
from rest_framework import serializers


class JasminGroupSerializer(serializers.Serializer):
    gid = serializers.CharField()


class JasminConnectorSerializer(serializers.Serializer):
    cid = serializers.CharField()


class JasminCredentialsSerializer(serializers.Serializer):
    authorizations = serializers.DictField()
    value_filters = serializers.DictField()
    defaults = serializers.DictField()
    quotas = serializers.DictField()
    quotas_updated = serializers.BooleanField()


class JasminUserSerializer(serializers.Serializer):
    password = serializers.CharField()
    username = serializers.CharField()
    group = JasminGroupSerializer()
    enabled = serializers.BooleanField()
    mt_credential = JasminCredentialsSerializer()
    smpps_credential = JasminCredentialsSerializer()


class JasminFilterSerializer(serializers.Serializer):
    userFor = serializers.ListSerializer(child=serializers.CharField())
    connector = JasminConnectorSerializer()
    user = serializers.CharField()
    group = serializers.CharField()
    source_addr = serializers.CharField()
    destination_addr = serializers.CharField()
    short_message = serializers.CharField()
    dateInterval = serializers.CharField()
    timeInterval = serializers.CharField()


class JasminRouteSerializer(serializers.Serializer):
    filters = serializers.ListSerializer(child=JasminFilterSerializer())
    connector = JasminConnectorSerializer()
    rate = serializers.IntegerField()

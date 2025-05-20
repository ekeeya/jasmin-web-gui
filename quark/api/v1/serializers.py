import logging

from rest_framework import serializers
from rest_framework.fields import SerializerMethodField

from quark.jasmin.models import JasminGroup, JasminRoute, JasminFilter, JasminSMPPConnector, JasminHTTPConnector
from quark.utils import json

logger = logging.getLogger(__name__)


def format_datetime(value):
    """

    :param value:
    :return:
    """
    return json.encode_datetime(value, micros=True) if value else None


class ReadSerializer(serializers.ModelSerializer):
    """
    Serializer that serializes Read objects. separation of logic, DFR uses the same serializer class for both read and write
    """

    def save(self, **kwargs):
        raise ValueError("Can't call save on a read serializer")


class WriteSerializer(serializers.Serializer):
    """
        DRF uses the view to decide if it's an update or new instance. Let's have the serializer do it.
    """

    def run_validation(self, data=serializers.empty):
        if not isinstance(data, dict):
            raise serializers.ValidationError(
                detail={"non_field_errors": ["Request body must be a single JSON object"]}
            )

        if not self.context["user"].is_active:
            raise serializers.ValidationError(detail={"non_field_errors": ["User must be active"]})

        return super().run_validation(data)


class JasminGroupReadSerializer(ReadSerializer):
    class Meta:
        model = JasminGroup
        fields = (
            "id",
            "gid",
            "description",
            "is_active"
        )


class JasminGroupWriteSerializer(WriteSerializer):
    gid = serializers.CharField(required=True)

    def validate_gid(self, value):
        if JasminGroup.objects.filter(gid=value).exists():
            raise serializers.ValidationError(f"Group with name code {value} already exist.")

        return value

    def save(self, **kwargs):
        form_data = self.validated_data
        workspace = self.context["workspace"]
        if self.instance:
            return self.instance.update(form_data)
        else:
            return JasminGroup.create(**form_data)


class JasminFilterReadSerializer(ReadSerializer):
    workspace = SerializerMethodField()

    def get_workspace(self, instance):
        return instance.workspace.name

    class Meta:
        model = JasminFilter
        fields = (
            "id",
            "nature",
            "param",
            "workspace",
            "filter_type"
        )


class JasminSMPPConnectorReadSerializer(ReadSerializer):
    config = serializers.SerializerMethodField()

    def get_config(self, instance):
        return instance.to_json()

    class Meta:
        model = JasminSMPPConnector
        fields = (
            "id",
            "cid",
            "connector_type",
            "host",
            "port",
            "username",
            "password",
            "config"
        )


class JasminHTTPConnectorReadSerializer(ReadSerializer):
    class Meta:
        model = JasminHTTPConnector
        fields = (
            "id",
            "cid",
            "connector_type",
            "base_url",
            "method",
            "description"
        )


class JasminRouterReadSerializer(ReadSerializer):
    filters = serializers.SerializerMethodField()
    smpp_connectors = serializers.SerializerMethodField()
    http_connectors = serializers.SerializerMethodField()

    def get_filters(self, instance):
        if instance.filters and len(instance.filters.all()) > 0:
            return JasminFilterReadSerializer(instance.filters, many=True).data
        return []

    def get_smpp_connectors(self, instance):
        if instance.smpp_connectors and len(instance.smpp_connectors.all()) > 0:
            return JasminSMPPConnectorReadSerializer(instance.smpp_connectors.all(), many=True).data
        return []

    def get_http_connectors(self, instance):
        if instance.http_connectors and len(instance.http_connectors.all()) > 0:
            return JasminHTTPConnectorReadSerializer(instance.http_connectors.all(), many=True).data

        return []

    class Meta:
        model = JasminRoute
        fields = (
            "id",
            "rate",
            "nature",
            "workspace",
            "order",
            "router_type",
            "filters",
            "smpp_connectors",
            "http_connectors"
        )

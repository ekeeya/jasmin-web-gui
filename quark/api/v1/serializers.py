import base64
import logging

from rest_framework import serializers

from quark.api.v1.fields import JoyceUniqueFieldValidator
from quark.utils import json
from quark.utils.utils import strprice

from quark.jasmin.models import JasminGroup

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

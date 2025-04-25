from rest_framework.pagination import LimitOffsetPagination
from rest_framework.renderers import JSONRenderer, BrowsableAPIRenderer
from rest_framework.throttling import ScopedRateThrottle

from quark.adapter.models import JasminGroup
from quark.api.helper import APISessionAuthentication, APIBasicAuthentication
from quark.api.v1.serializers import JasminGroupWriteSerializer, JasminGroupReadSerializer
from quark.api.views import WriteAPIMixin, BaseAPIView, ListAPIMixin


class BaseEndpoint(BaseAPIView):
    """
    Base class of all our API V2 endpoints
    """

    authentication_classes = (APISessionAuthentication, APIBasicAuthentication)
    permission_classes = ()
    renderer_classes = (JSONRenderer, BrowsableAPIRenderer)
    throttle_classes = (ScopedRateThrottle,)
    throttle_scope = "v1"


class JasminGroupEndPoint(ListAPIMixin, WriteAPIMixin, BaseEndpoint):
    model = JasminGroup
    write_serializer_class = JasminGroupWriteSerializer
    serializer_class = JasminGroupReadSerializer
    pagination_class = LimitOffsetPagination

    def get_queryset(self):
        queryset = super().get_queryset()

        return queryset.filter(is_active=True)

    def filter_queryset(self, queryset):
        params = self.request.query_params

        gid = params.get('name')

        # Filter by group
        if gid is not None:
            queryset = queryset.filter(gid=gid)

        # setup filter by before/after on start_date
        return self.filter_before_after(queryset, "created_on")

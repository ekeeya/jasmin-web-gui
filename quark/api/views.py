import contextlib
import logging
import mimetypes

import iso8601
from django.http import FileResponse
from rest_framework import generics, mixins, status
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from django.db import transaction
from quark.api.helper import InvalidQueryError
from quark.utils.mixins.mixins import NonAtomicMixin

logger = logging.getLogger(__name__)


class BaseAPIView(NonAtomicMixin, generics.GenericAPIView):
    """
    Base class of all our API endpoints
    """

    model = None
    model_manager = "objects"
    lookup_params = {"id": "id"}

    def derive_queryset(self):
        return getattr(self.model, self.model_manager).all()

    def get_queryset(self):
        qs = self.derive_queryset()

        # if this is a get request, fetch from readonly database
        if self.request.method == "GET":
            qs = qs.using("readonly")

        return qs

    def get_lookup_values(self):
        """
        Extracts lookup_params from the request URL, e.g. {"id": "123..."}
        """
        lookup_values = {}
        for param, field in self.lookup_params.items():
            if param in self.request.query_params:
                param_value = self.request.query_params[param]

                lookup_values[field] = param_value

        if len(lookup_values) > 1:
            raise InvalidQueryError(
                "URL can only contain one of the following parameters: " + ", ".join(sorted(self.lookup_params.keys()))
            )

        return lookup_values

    def get_object(self):
        queryset = self.get_queryset().filter(**self.lookup_values)

        return generics.get_object_or_404(queryset)

    def get_int_param(self, name):
        param = self.request.query_params.get(name)
        try:
            return int(param) if param is not None else None
        except ValueError:
            raise InvalidQueryError("Value for %s must be an integer" % name)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["workspace"] = self.request.workspace
        context["user"] = self.request.user
        return context

    def is_docs(self):
        """

        :return: Document
        """
        return "format" not in self.kwargs


class ListAPIMixin(mixins.ListModelMixin):
    """
    Mixin for any endpoint which returns a list of objects from a GET request
    """

    exclusive_params = ()

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    def list(self, request, *args, **kwargs):
        self.check_query(self.request.query_params)

        if self.is_docs():
            # if this is just a request to browse the endpoint docs, don't make a query
            return Response([])
        else:
            return super().list(request, *args, **kwargs)

    def check_query(self, params):
        # check user hasn't provided values for more than one of any exclusive params
        if sum([(1 if params.get(p) else 0) for p in self.exclusive_params]) > 1:
            raise InvalidQueryError("You may only specify one of the %s parameters" % ", ".join(self.exclusive_params))

    def filter_before_after(self, queryset, field):
        """
        Filters the queryset by the before/after params if are provided
        """
        before = self.request.query_params.get("before")
        if before:
            try:
                before = iso8601.parse_date(before)
                queryset = queryset.filter(**{field + "__lte": before})
            except ValueError:
                queryset = queryset.filter(pk=-1)

        after = self.request.query_params.get("after")
        if after:
            try:
                after = iso8601.parse_date(after)
                queryset = queryset.filter(**{field + "__gte": after})
            except ValueError:
                queryset = queryset.filter(pk=-1)

        return queryset

    def paginate_queryset(self, queryset):
        page = super().paginate_queryset(queryset)

        # give views a chance to prepare objects for serialization
        self.prepare_for_serialization(page, using=queryset.db)

        return page

    def prepare_for_serialization(self, page, using: str):
        """
        Views can override this to do things like bulk cache initialization of result objects
        """
        pass


class WriteAPIMixin:
    """
    Mixin for any endpoint which can create or update objects with a write serializer. Our approach differs a bit from
    the REST framework default way as we use POST requests for both create and update operations, and use separate
    serializers for reading and writing.
    """

    write_serializer_class = None
    write_with_transaction = True

    def post_save(self, instance):
        """
        Can be overridden to add custom handling after object creation
        """
        pass

    def post(self, request, *args, **kwargs):
        self.lookup_values = self.get_lookup_values()

        # determine if this is an update of an existing object or a create of a new object
        if self.lookup_values:
            instance = self.get_object()
        else:
            instance = None

        context = self.get_serializer_context()
        context["lookup_values"] = self.lookup_values
        context["instance"] = instance

        serializer = self.write_serializer_class(instance=instance, data=request.data, context=context)

        if serializer.is_valid():
            mgr = transaction.atomic() if self.write_with_transaction else contextlib.suppress()
            with mgr:
                output = serializer.save()
                self.post_save(output)
                return self.render_write_response(output, context)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def render_write_response(self, write_output, context):
        response_serializer = self.serializer_class(instance=write_output, context=context)

        # if we're also a list view, we can re-use any serialization preparation it uses
        if hasattr(self, "prepare_for_serialization"):
            self.prepare_for_serialization([write_output], using="default")

        # if we created a new object, notify caller by returning 201
        status_code = status.HTTP_200_OK if context["instance"] else status.HTTP_201_CREATED

        return Response(response_serializer.data, status=status_code)


class DeleteAPIMixin(mixins.DestroyModelMixin):
    """
    Mixin for any endpoint that can delete objects with a DELETE request
    """

    def delete(self, request, *args, **kwargs):
        self.lookup_values = self.get_lookup_values()

        if not self.lookup_values:
            raise InvalidQueryError(
                "URL must contain one of the following parameters: " + ", ".join(sorted(self.lookup_params.keys()))
            )

        instance = self.get_object()
        if self.is_system_instance(instance):
            return Response({"detail": "Cannot delete system object."}, status=status.HTTP_403_FORBIDDEN)

        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def perform_destroy(self, instance):
        instance.release(self.request.user)


class FileUploadAPIMixin:
    parser_classes = (MultiPartParser,)

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data, context=self.get_serializer_context())
        if serializer.is_valid():
            result = serializer.save()
            if isinstance(result, Response):
                return result  # return as is
            return Response(result, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class FileDownloadAPIMixin:
    """
       When we need the actual file, we shall do a post as opposed to a GET.
       Logic will get complicated if we try to use GET for browser reports and then file extractions
    """
    special_params = (
        "report_type", "before", "after", "module", "limit", "offset",
        "count")  # we shall not include these in filter_params to pass to Report

    def get_filter_params(self):
        if self.request.method == 'GET':
            params = clean_query_params(self.request.query_params)  # turn to mutable dict
        else:
            params = copy.deepcopy(self.request.data)

        for param in self.special_params:
            if param in params:
                params.pop(param)

        return dict(params)

    def post(self, request, *args, **kwargs):
        # self.renderer_classes = FileDownloadRenderer  # set it for only when post
        serializer = self.write_serializer_class(data=request.data, context=self.get_serializer_context())
        if serializer.is_valid():
            result = serializer.save()
            if isinstance(result, Response):
                return result
            if isinstance(result, dict):
                # this is an error for sure return as is
                return Response(result, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            file_path, filename = result  # The result is our file path and name
            mimetype, _ = mimetypes.guess_type(file_path)
            try:
                # open it with resources (hahaha)
                file = open(file_path, 'rb')
                response = FileResponse(file, content_type=mimetype)
                response['Content-Disposition'] = 'attachment; filename="%s"' % filename
                response['Access-Control-Expose-Headers'] = "Content-Disposition"
                return response
            except Exception as error:
                logger.exception(error)
                return Response(dict(success=False, message=str(error)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            finally:
                # os.remove(file_path)  # clear the written file off the disc
                pass

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

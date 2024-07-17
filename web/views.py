import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from web.renderers.renderers import PlainTextRenderer, CustomPlainTextRenderer

logger = logging.getLogger('main')


class SMSCallback(APIView):
    renderer_classes = [PlainTextRenderer, CustomPlainTextRenderer]

    def post(self, request, *args, **kwargs):
        try:
            # Handle form-encoded data
            if request.content_type == 'application/x-www-form-urlencoded':
                data = request.POST
            else:  # Default to JSON data
                data = request.data
            logger.info(f"Received DLR: {data}")

            return Response('ACK/Jasmin', status=status.HTTP_200_OK, content_type='text/plain')
        except Exception as e:
            logger.error(f"Error processing DLR: {e}")
        return Response('Error', status=status.HTTP_500_INTERNAL_SERVER_ERROR, content_type='text/plain')

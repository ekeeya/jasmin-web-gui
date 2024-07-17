from rest_framework import renderers


class PlainTextRenderer(renderers.BaseRenderer):
    media_type = 'text/plain'
    format = 'txt'
    charset = 'utf-8'

    def render(self, data, media_type=None, renderer_context=None):
        if isinstance(data, dict):
            if 'detail' in data:
                return data['detail'].encode(self.charset)
        return data.encode(self.charset)


class CustomPlainTextRenderer(renderers.BaseRenderer):
    media_type = None
    format = 'txt'
    charset = 'utf-8'

    def render(self, data, media_type=None, renderer_context=None):
        if isinstance(data, dict):
            if 'detail' in data:
                return data['detail'].encode(self.charset)
        return data.encode(self.charset)

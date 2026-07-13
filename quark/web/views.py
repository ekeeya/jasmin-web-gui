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

import logging

from django.http import HttpResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from smartmin.views import SmartTemplateView

from quark.messaging.views.views import (
    CONSOLE_MODE_SESSION_KEY,
    MODE_CONFIGURE,
    MODE_OPERATE,
)
from quark.web.dashboard import configure_dashboard_stats, operate_dashboard_stats
from quark.web.renderers.renderers import PlainTextRenderer, CustomPlainTextRenderer
from quark.workspace.views.mixins import WorkspacePermsMixin

logger = logging.getLogger('main')


class SMSCallback(APIView):
    """Legacy stub kept for imports; /dlr now uses messaging.DLRCallbackView."""

    renderer_classes = [PlainTextRenderer, CustomPlainTextRenderer]

    def post(self, request, *args, **kwargs):
        try:
            if request.content_type == 'application/x-www-form-urlencoded':
                data = request.POST
            else:
                data = request.data
            logger.info(f"Received DLR: {data}")

            return Response('ACK/Jasmin', status=status.HTTP_200_OK, content_type='text/plain')
        except Exception as e:
            logger.error(f"Error processing DLR: {e}")
        return Response('Error', status=status.HTTP_500_INTERNAL_SERVER_ERROR, content_type='text/plain')


class Home(WorkspacePermsMixin, SmartTemplateView):
    """Mode-aware dashboard: Configure inventory or Operate SMS metrics."""

    title = "Dashboard"
    permission = "workspace.workspace_dashboard"
    template_name = "home/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        workspace = self.request.workspace
        context["workspace"] = workspace
        context["user"] = self.request.user

        mode = self.request.session.get(CONSOLE_MODE_SESSION_KEY, MODE_CONFIGURE)
        if mode not in (MODE_CONFIGURE, MODE_OPERATE):
            mode = MODE_CONFIGURE
        context["dashboard_mode"] = mode

        if not workspace:
            context["totals"] = {}
            context["recent"] = []
            context["config_counts"] = {}
            context["checklist"] = []
            return context

        if mode == MODE_OPERATE:
            context.update(operate_dashboard_stats(workspace))
        else:
            context.update(configure_dashboard_stats(workspace))
        return context


class Landing(SmartTemplateView):
    """
    The main dashboard view
    """

    title = "Landing Page"
    permission = None
    template_name = "home/landing.html"


def profile(request, user_id):
    return HttpResponse("<h1>Page was found</h1>")

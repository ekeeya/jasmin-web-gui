#
#  Copyright (c) 2026
#
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.views import View
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from smartmin.views import SmartCRUDL, SmartFormView, SmartReadView, SmartTemplateView

import logging

from quark.jasmin.models import JasminUser
from quark.messaging.clients import JasminHttpClient
from quark.messaging.forms import BulkSendSMSForm, SendSMSForm
from quark.messaging.models import OutboundMessage, dlr_callback_url
from quark.messaging.services import submit_bulk, submit_outbound_message
from quark.web.dashboard import operate_dashboard_stats
from quark.web.renderers.renderers import CustomPlainTextRenderer, PlainTextRenderer
from quark.workspace.views.base import BaseListView
from quark.workspace.views.mixins import WorkspacePermsMixin

logger = logging.getLogger(__name__)


CONSOLE_MODE_SESSION_KEY = "joyce_console_mode"
MODE_CONFIGURE = "configure"
MODE_OPERATE = "operate"


class SetConsoleModeView(LoginRequiredMixin, WorkspacePermsMixin, View):
    """Switch between Configure and Operate consoles (same workspace + user)."""

    permission = "workspace.workspace_dashboard"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not self.has_permission(request, *args, **kwargs):
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied()
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        mode = (request.POST.get("mode") or "").strip().lower()
        if mode not in (MODE_CONFIGURE, MODE_OPERATE):
            mode = MODE_CONFIGURE
        request.session[CONSOLE_MODE_SESSION_KEY] = mode
        return HttpResponseRedirect(reverse("dashboard.dashboard_home"))

    def get(self, request, *args, **kwargs):
        mode = (request.GET.get("mode") or "").strip().lower()
        if mode not in (MODE_CONFIGURE, MODE_OPERATE):
            mode = MODE_CONFIGURE
        request.session[CONSOLE_MODE_SESSION_KEY] = mode
        return HttpResponseRedirect(reverse("dashboard.dashboard_home"))


class SendSMSView(WorkspacePermsMixin, SmartFormView):
    title = "Send SMS"
    permission = "messaging.outboundmessage_send"
    template_name = "messaging/send.html"
    form_class = SendSMSForm
    success_message = "Message submitted to Jasmin"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["workspace"] = self.request.workspace
        return kwargs

    def form_valid(self, form):
        message = submit_outbound_message(
            workspace=self.request.workspace,
            jasmin_user=form.cleaned_data["jasmin_user"],
            to_addr=form.cleaned_data["to_addr"],
            from_addr=form.cleaned_data.get("from_addr") or "",
            content=form.cleaned_data["content"],
            dlr_level=int(form.cleaned_data["dlr_level"]),
            priority=int(form.cleaned_data.get("priority") or 0),
            created_by=self.request.user,
        )
        if message.status == OutboundMessage.STATUS_FAILED:
            form.add_error(None, message.error_message or "Jasmin rejected the message")
            return self.form_invalid(form)
        messages.success(
            self.request,
            f"Submitted to {message.to_addr}. Jasmin id: {message.jasmin_msg_id or '—'}",
        )
        return HttpResponseRedirect(reverse("messaging.outboundmessage_read", args=[message.pk]))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["workspace"] = self.request.workspace
        context["user"] = self.request.user
        context["send_mode"] = "single"
        context["dlr_callback_url"] = dlr_callback_url()
        return context


class BulkSendSMSView(WorkspacePermsMixin, SmartFormView):
    title = "Bulk SMS"
    permission = "messaging.outboundmessage_send"
    template_name = "messaging/bulk_send.html"
    form_class = BulkSendSMSForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["workspace"] = self.request.workspace
        return kwargs

    def form_valid(self, form):
        batch_id, submitted = submit_bulk(
            workspace=self.request.workspace,
            jasmin_user=form.cleaned_data["jasmin_user"],
            recipients=form.cleaned_data["recipients"],
            content=form.cleaned_data["content"],
            from_addr=form.cleaned_data.get("from_addr") or "",
            dlr_level=int(form.cleaned_data["dlr_level"]),
            created_by=self.request.user,
        )
        ok = sum(1 for m in submitted if m.status == OutboundMessage.STATUS_SUBMITTED)
        queued = sum(1 for m in submitted if m.status == OutboundMessage.STATUS_QUEUED)
        fail = len(submitted) - ok - queued
        if queued and not ok:
            messages.success(
                self.request,
                f"Bulk batch {batch_id}: {queued} queued for async submit ({len(submitted)} total).",
            )
        else:
            messages.success(
                self.request,
                f"Bulk batch {batch_id}: {ok} submitted, {fail} failed"
                + (f", {queued} queued" if queued else "")
                + f" ({len(submitted)} total).",
            )
        return HttpResponseRedirect(f"{reverse('messaging.outboundmessage_list')}?search={batch_id}")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["workspace"] = self.request.workspace
        context["user"] = self.request.user
        context["send_mode"] = "bulk"
        context["dlr_callback_url"] = dlr_callback_url()
        return context


class OutboundMessageCRUDL(SmartCRUDL):
    model = OutboundMessage
    actions = ("list", "read")

    class List(BaseListView):
        permission = "messaging.outboundmessage_list"
        title = "Message log"
        search_fields = ("to_addr__icontains", "from_addr__icontains", "jasmin_msg_id__icontains", "batch_id__icontains", "content__icontains")
        default_order = ("-created_on",)
        fields = ("to_addr", "status", "jasmin_user", "batch_kind", "jasmin_msg_id", "created_on")
        field_config = {
            "to_addr": {"label": "To"},
            "jasmin_msg_id": {"label": "Jasmin ID"},
            "batch_kind": {"label": "Kind"},
            "created_on": {"label": "Created"},
        }
        add_button = False
        template_name = "messaging/message_list.html"

        def get_context_data(self, **kwargs):
            context = super().get_context_data(**kwargs)
            context["workspace"] = self.request.workspace
            context["user"] = self.request.user
            qs = self.derive_queryset()
            context["status_counts"] = {
                row["status"]: row["c"]
                for row in qs.values("status").annotate(c=Count("id"))
            }
            return context

    class Read(WorkspacePermsMixin, SmartReadView):
        permission = "messaging.outboundmessage_read"
        title = "Message detail"
        fields = (
            "to_addr",
            "from_addr",
            "content",
            "status",
            "jasmin_msg_id",
            "dlr_status",
            "jasmin_user",
            "batch_id",
            "batch_kind",
            "dlr_level",
            "submitted_at",
            "delivered_at",
            "last_dlr_at",
            "submit_response",
            "error_message",
            "created_on",
        )
        template_name = "messaging/message_detail.html"

        def get_queryset(self):
            return OutboundMessage.objects.filter(workspace=self.request.workspace)

        def get_context_data(self, **kwargs):
            context = super().get_context_data(**kwargs)
            context["workspace"] = self.request.workspace
            context["user"] = self.request.user
            return context


class BalanceRateView(WorkspacePermsMixin, SmartTemplateView):
    title = "Balance & rate"
    permission = "messaging.outboundmessage_send"
    template_name = "messaging/balance.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        workspace = self.request.workspace
        context["workspace"] = workspace
        context["user"] = self.request.user
        users = JasminUser.objects.filter(group__workspace=workspace, enabled=True).order_by("username")
        context["jasmin_users"] = users

        selected_id = self.request.GET.get("user") or self.request.POST.get("jasmin_user")
        selected = users.filter(pk=selected_id).first() if selected_id else users.first()
        context["selected_user"] = selected
        context["balance_text"] = ""
        context["rate_text"] = ""
        context["lookup_error"] = ""

        if selected and self.request.method == "GET" and self.request.GET.get("check"):
            from quark.jasmin.connection import JasminNotConfigured, resolve_jasmin_connection

            try:
                connection = resolve_jasmin_connection(workspace)
                client = JasminHttpClient(base_url=connection.http_api_url)
            except JasminNotConfigured as exc:
                context["lookup_error"] = str(exc)
                return context

            bal = client.balance(username=selected.username, password=selected.password)
            rate = client.rate(username=selected.username, password=selected.password)
            if bal.ok:
                context["balance_text"] = bal.text
            else:
                context["lookup_error"] = bal.error or "Balance lookup failed"
            if rate.ok:
                context["rate_text"] = rate.text
            elif not context["lookup_error"]:
                context["lookup_error"] = rate.error or "Rate lookup failed"
        return context


class DLRCallbackView(APIView):
    """
    Public Jasmin DLR callback. Must remain CSRF-exempt and return plain ACK/Jasmin.
    Optionally enqueues async forward to the workspace external DLR URL.
    """

    authentication_classes = []
    permission_classes = [AllowAny]
    renderer_classes = [PlainTextRenderer, CustomPlainTextRenderer]

    def post(self, request, *args, **kwargs):
        try:
            if request.content_type == "application/x-www-form-urlencoded":
                data = request.POST
            else:
                data = request.data

            payload = {k: data.get(k) for k in data.keys()}
            logger.info("Received DLR: %s", payload)
            msg_id = (
                payload.get("id")
                or payload.get("message_id")
                or payload.get("msgid")
                or ""
            )
            msg_id = str(msg_id).strip()
            if msg_id:
                message = (
                    OutboundMessage.objects.filter(jasmin_msg_id=msg_id)
                    .select_related("workspace")
                    .order_by("-created_on")
                    .first()
                )
                if message:
                    message.apply_dlr(payload)
                    try:
                        from quark.messaging.tasks import enqueue_external_dlr_forward

                        enqueue_external_dlr_forward(message)
                    except Exception:
                        logger.exception(
                            "Failed to enqueue external DLR forward for message %s",
                            message.pk,
                        )

            return Response("ACK/Jasmin", status=status.HTTP_200_OK, content_type="text/plain")
        except Exception:
            logger.exception("Error processing DLR")
            return Response("Error", status=status.HTTP_500_INTERNAL_SERVER_ERROR, content_type="text/plain")

    def get(self, request, *args, **kwargs):
        # Some connectors may use GET callbacks
        return self.post(request, *args, **kwargs)


class BatchCallbackView(APIView):
    """
    Public Jasmin REST sendbatch success/error callback.
    Updates jasmin_msg_id / status for matching OutboundMessage rows.
    """

    authentication_classes = []
    permission_classes = [AllowAny]
    renderer_classes = [PlainTextRenderer, CustomPlainTextRenderer]

    def post(self, request, *args, **kwargs):
        try:
            if request.content_type == "application/x-www-form-urlencoded":
                data = request.POST
            else:
                data = request.data
            payload = {k: data.get(k) for k in data.keys()}
            # Also accept query params (Jasmin may GET)
            for k, v in request.query_params.items():
                payload.setdefault(k, v)
            logger.info("Received batch callback: %s", payload)
            from quark.messaging.services import apply_batch_callback

            apply_batch_callback(payload)
            return Response("ACK/Jasmin", status=status.HTTP_200_OK, content_type="text/plain")
        except Exception:
            logger.exception("Error processing batch callback")
            return Response("Error", status=status.HTTP_500_INTERNAL_SERVER_ERROR, content_type="text/plain")

    def get(self, request, *args, **kwargs):
        return self.post(request, *args, **kwargs)


def dashboard_stats(workspace) -> dict:
    """Aggregate counts for the operate dashboard (compat wrapper)."""
    return operate_dashboard_stats(workspace)

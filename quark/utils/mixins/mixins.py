import logging

from django.db import transaction
from django import forms
from django.http import HttpResponse, JsonResponse, HttpResponseRedirect

from quark.utils.fields import CheckboxInputWidget

logger = logging.getLogger(__name__)


class NonAtomicMixin:
    """
        Mixin to disable automatic transaction wrapping of a class based view
    """

    @transaction.non_atomic_requests
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)


class PostOnlyMixin:
    """Mixin to make a class based view be POST only"""

    def get(self, *args, **kwargs):
        return HttpResponse("Only Method PST is allowed", status=405)


class RequireAuthMixin:
    """Mixin to redirect the user to login page if they haven't authenticated."""

    recent_auth_seconds = 10 * 60
    recent_auth_includes_formax = False

    def pre_process(self, request, *args, **kwargs):
        # TODO we shall complete it
        pass


class SystemOnlyMixin:
    """Mixin to ensure the view is only accessed by system users"""

    def has_permission(self, request, *args, **kwargs):
        return self.request.user.is_staff or request.user.is_superuser


class FormMixin:
    """
    Mixin to replace form field controls with our custom based widgets
    """

    def customize_form_field(self, name, field):
        attrs = field.widget.attrs if field.widget.attrs else {}

        # don't replace the widget if it is already one of us
        if isinstance(
                field.widget,
                (forms.widgets.HiddenInput, CheckboxInputWidget, RadioSelectWidget, InputTextWidget, SelectWidget,
                 MultiSelectWidget),
        ):
            return field

        if isinstance(field.widget, (forms.widgets.Textarea,)):
            attrs["textarea"] = True
            field.widget = InputTextWidget(attrs=attrs)
        elif isinstance(field.widget, (forms.widgets.PasswordInput,)):  # pragma: needs cover
            attrs["password"] = True
            field.widget = InputTextWidget(attrs=attrs)
        elif isinstance(
                field.widget,
                (forms.widgets.TextInput, forms.widgets.EmailInput, forms.widgets.URLInput),
        ):
            field.widget = InputTextWidget(attrs=attrs)
        elif isinstance(field.widget, (forms.widgets.Select,)):
            if isinstance(field, (forms.models.ModelMultipleChoiceWidget,)):
                field.widget = MultiSelectWidget(attrs)  # pragma: needs cover
            else:
                field.widget = SelectWidget(attrs)

            field.widget.choices = field.choices
        elif isinstance(field.widget, (forms.widgets.CheckboxInput,)):
            field.widget = CheckboxInputWidget(attrs)

        return field


class ModalFormMixin:
    """
        Handles invalid form submissions and returns a JSON response on form_invalid for modal(ajax) creates
    """

    def form_invalid(self, form):
        errors = form.errors
        message = "Form submission failed, see errors for details"
        response = dict(errors=errors, success=False, message=message)
        return JsonResponse(response, status=400, safe=False)

    def form_valid(self, form):
        message = "Action executed successfully"
        if "HTTP_X_AJAX_MODAL" in self.request.META:
            response = dict(success=True, message=message, redirect_to=self.get_success_url())
            return JsonResponse(response, safe=False)
        return HttpResponseRedirect(self.get_success_url())

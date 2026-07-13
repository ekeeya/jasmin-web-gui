#  Copyright (c) 2025
#  File created on 2025/4/25
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
from django import forms
from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django_countries.fields import CountryField
from timezone_field import TimeZoneFormField

from quark.utils.crypto import CredentialsKeyError, encrypt_secret, looks_encrypted
from quark.workspace.models import User, WorkSpace

# Shared field chrome for the workspace settings page (avoids Smartmin FormMixin wrappers)
_SETTINGS_INPUT = {
    "class": (
        "w-full rounded-none border border-neutral-300 bg-white px-3 py-2 text-sm "
        "text-neutral-900 placeholder:text-neutral-400 focus:border-neutral-900 "
        "focus:outline-none focus:ring-1 focus:ring-neutral-900"
    ),
}


def _text(**extra):
    attrs = {**_SETTINGS_INPUT, **extra}
    return forms.TextInput(attrs=attrs)


def _number(**extra):
    attrs = {**_SETTINGS_INPUT, "type": "number", **extra}
    return forms.NumberInput(attrs=attrs)


def _password(**extra):
    attrs = {**_SETTINGS_INPUT, "autocomplete": "new-password", **extra}
    return forms.PasswordInput(render_value=False, attrs=attrs)


class BaseWorkspaceForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        # Inject the workspace
        self.workspace = kwargs["workspace"]
        del kwargs["workspace"]
        super().__init__(*args, **kwargs)

    def clean(self):
        self.cleaned_data = super().clean()
        self.cleaned_data['workspace'] = self.workspace

        return self.cleaned_data


class WorkspaceSettingsForm(forms.ModelForm):
    jasmin_link = forms.ChoiceField(
        choices=(
            (WorkSpace.JASMIN_LINK_DEMO, "Local demo Jasmin"),
            (WorkSpace.JASMIN_LINK_CUSTOM, "My own Jasmin"),
        ),
        widget=forms.RadioSelect,
        required=True,
        label="Jasmin connection",
    )
    jasmin_router_pb_host = forms.CharField(
        required=False, label="Host", widget=_text(placeholder="jasmin.example.com")
    )
    jasmin_router_pb_port = forms.IntegerField(
        required=False, label="Port", widget=_number(min="1", placeholder="8988")
    )
    jasmin_router_pb_username = forms.CharField(
        required=False, label="Username", widget=_text(placeholder="radmin")
    )
    jasmin_router_pb_password = forms.CharField(
        required=False,
        label="Password",
        widget=_password(),
        help_text="Leave blank to keep the current password. Stored encrypted.",
    )
    jasmin_smpp_pb_host = forms.CharField(
        required=False, label="Host", widget=_text(placeholder="jasmin.example.com")
    )
    jasmin_smpp_pb_port = forms.IntegerField(
        required=False, label="Port", widget=_number(min="1", placeholder="8989")
    )
    jasmin_smpp_pb_username = forms.CharField(
        required=False, label="Username", widget=_text(placeholder="cmadmin")
    )
    jasmin_smpp_pb_password = forms.CharField(
        required=False,
        label="Password",
        widget=_password(),
        help_text="Leave blank to keep the current password. Stored encrypted.",
    )
    jasmin_http_api_url = forms.URLField(
        required=False,
        label="Base URL",
        widget=_text(placeholder="http://jasmin.example.com:1401"),
        help_text="Used for /send, /balance, and /rate.",
    )
    jasmin_rest_api_url = forms.URLField(
        required=False,
        label="REST API base URL",
        widget=_text(placeholder="http://jasmin.example.com:8080"),
        help_text="",
    )
    jasmin_user_sync_interval_mins = forms.IntegerField(
        min_value=0,
        required=True,
        label="User sync interval (minutes)",
        help_text="How often to pull live quotas into Joyce. 0 disables automatic sync.",
        widget=_number(min="0"),
    )
    messaging_api_enabled = forms.BooleanField(
        required=False,
        label="Enable Joyce messaging API",
        help_text="Allow external apps to POST SMS through Joyce with a bearer token (send endpoint only).",
        widget=forms.CheckboxInput(attrs={"class": "checkbox checkbox-sm"}),
    )
    external_dlr_url = forms.URLField(
        required=False,
        label="External DLR URL",
        widget=_text(placeholder="https://your-app.example.com/webhooks/dlr"),
        help_text="Optional. After Joyce handles a DLR, it is forwarded here (async, with retries).",
    )
    external_dlr_method = forms.ChoiceField(
        required=False,
        choices=(("POST", "POST"), ("GET", "GET")),
        initial="POST",
        label="External DLR method",
        widget=forms.Select(
            attrs={
                "class": (
                    "w-full rounded-none border border-neutral-300 bg-white px-3 py-2 text-sm "
                    "text-neutral-900 focus:border-neutral-900 focus:outline-none focus:ring-1 "
                    "focus:ring-neutral-900"
                )
            }
        ),
    )
    external_dlr_retry_delay_secs = forms.IntegerField(
        min_value=1,
        required=False,
        initial=60,
        label="DLR forward retry delay (seconds)",
        widget=_number(min="1"),
        help_text="Default 60. Wait this long between forward retries.",
    )
    external_dlr_max_retries = forms.IntegerField(
        min_value=1,
        max_value=20,
        required=False,
        initial=5,
        label="DLR forward max retries",
        widget=_number(min="1", max="20"),
        help_text="Default 5.",
    )

    class Meta:
        model = WorkSpace
        fields = (
            "jasmin_link",
            "jasmin_router_pb_host",
            "jasmin_router_pb_port",
            "jasmin_router_pb_username",
            "jasmin_router_pb_password",
            "jasmin_smpp_pb_host",
            "jasmin_smpp_pb_port",
            "jasmin_smpp_pb_username",
            "jasmin_smpp_pb_password",
            "jasmin_http_api_url",
            "jasmin_rest_api_url",
            "jasmin_user_sync_interval_mins",
            "messaging_api_enabled",
            "external_dlr_url",
            "external_dlr_method",
            "external_dlr_retry_delay_secs",
            "external_dlr_max_retries",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Never bind encrypted secrets into the HTML form
        self.initial["jasmin_router_pb_password"] = ""
        self.initial["jasmin_smpp_pb_password"] = ""

        if self.instance and self.instance.pk:
            if self.instance.jasmin_router_pb_password:
                self.fields["jasmin_router_pb_password"].help_text = (
                    "Password is set. Leave blank to keep it."
                )
                self.fields["jasmin_router_pb_password"].widget.attrs["placeholder"] = "••••••••"
            if self.instance.jasmin_smpp_pb_password:
                self.fields["jasmin_smpp_pb_password"].help_text = (
                    "Password is set. Leave blank to keep it."
                )
                self.fields["jasmin_smpp_pb_password"].widget.attrs["placeholder"] = "••••••••"

    def clean(self):
        cleaned = super().clean()
        link = cleaned.get("jasmin_link") or WorkSpace.JASMIN_LINK_UNSET
        cleaned["jasmin_link"] = link

        if link == WorkSpace.JASMIN_LINK_CUSTOM:
            required = {
                "jasmin_router_pb_host": "Router PB host",
                "jasmin_router_pb_port": "Router PB port",
                "jasmin_router_pb_username": "Router PB username",
                "jasmin_smpp_pb_host": "SMPP PB host",
                "jasmin_smpp_pb_port": "SMPP PB port",
                "jasmin_smpp_pb_username": "SMPP PB username",
                "jasmin_http_api_url": "HTTP API base URL",
            }
            for field, label in required.items():
                if not cleaned.get(field):
                    self.add_error(field, f"{label} is required.")

            for field in ("jasmin_router_pb_password", "jasmin_smpp_pb_password"):
                new_val = cleaned.get(field)
                existing = getattr(self.instance, field, "") if self.instance else ""
                if not new_val and not existing:
                    self.add_error(field, "Password is required.")

            if not getattr(settings, "JOYCE_CREDENTIALS_KEY", ""):
                raise forms.ValidationError(
                    "JOYCE_CREDENTIALS_KEY is not configured on this Joyce server. "
                    "Custom Jasmin passwords cannot be stored until an admin sets it."
                )

        return cleaned

    def save(self, commit=True):
        import secrets

        instance = super().save(commit=False)
        link = self.cleaned_data.get("jasmin_link") or WorkSpace.JASMIN_LINK_UNSET

        if link == WorkSpace.JASMIN_LINK_DEMO:
            instance.clear_jasmin_custom_connection(save=False)
            instance.jasmin_link = WorkSpace.JASMIN_LINK_DEMO
        else:
            for field in ("jasmin_router_pb_password", "jasmin_smpp_pb_password"):
                new_val = (self.cleaned_data.get(field) or "").strip()
                if new_val:
                    if looks_encrypted(new_val):
                        setattr(instance, field, new_val)
                    else:
                        try:
                            setattr(instance, field, encrypt_secret(new_val))
                        except CredentialsKeyError as exc:
                            raise forms.ValidationError(str(exc)) from exc
                else:
                    setattr(instance, field, getattr(self.instance, field, "") or "")

            for field in ("jasmin_router_pb_password", "jasmin_smpp_pb_password"):
                val = getattr(instance, field, "")
                if val and not looks_encrypted(val):
                    try:
                        setattr(instance, field, encrypt_secret(val))
                    except CredentialsKeyError as exc:
                        raise forms.ValidationError(str(exc)) from exc

        enabled = bool(self.cleaned_data.get("messaging_api_enabled"))
        instance.messaging_api_enabled = enabled
        # Auto-generate on first enable; keep existing token otherwise.
        if enabled and not (instance.messaging_api_token or "").strip():
            import secrets

            instance.messaging_api_token = secrets.token_urlsafe(32)

        if self.cleaned_data.get("external_dlr_retry_delay_secs") in (None, ""):
            instance.external_dlr_retry_delay_secs = 60
        if self.cleaned_data.get("external_dlr_max_retries") in (None, ""):
            instance.external_dlr_max_retries = 5
        if not self.cleaned_data.get("external_dlr_method"):
            instance.external_dlr_method = "POST"

        if commit:
            instance.save()
        return instance


class SignupForm(forms.ModelForm):
    """
    Signup for new organizations
    """

    first_name = forms.CharField(
        max_length=User._meta.get_field("first_name").max_length,
        widget=forms.TextInput(attrs={"widget_only": True, "placeholder": "First name"}),
    )
    last_name = forms.CharField(
        max_length=User._meta.get_field("last_name").max_length,
        widget=forms.TextInput(attrs={"widget_only": True, "placeholder": "Last name"}),
    )

    username = forms.CharField(
        max_length=User._meta.get_field("username").max_length,
        widget=forms.TextInput(attrs={"widget_only": True, "placeholder": "example"}),
    )

    email = forms.EmailField(
        max_length=User._meta.get_field("email").max_length,
        widget=forms.EmailInput(attrs={"widget_only": True, "placeholder": "example@domain.com"}),
    )

    country = CountryField().formfield()

    timezone = TimeZoneFormField(help_text="The timezone for your workspace")

    password = forms.CharField(
        widget=forms.PasswordInput(attrs={"hide_label": True, "password": True, "placeholder": "Password"}),
        validators=[validate_password],
        help_text="At least six characters or more",
    )

    name = forms.CharField(
        label="Workspace",
        max_length=WorkSpace._meta.get_field("name").max_length,
        widget=forms.TextInput(attrs={
            "required": True,
            "widget_only": True,
            "placeholder": "Thothcode Dynamics, Inc."
        }),
    )

    def clean_email(self):
        email = self.cleaned_data["email"]
        if email:
            if User.objects.filter(username__iexact=email):
                raise forms.ValidationError("That email address is already used")

        return email.lower()

    class Meta:
        model = WorkSpace
        fields = ("first_name", "last_name", "username", "country", "email", "timezone", "password", "name",)

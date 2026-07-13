#
#  Copyright (c) 2026
#
import re

from django import forms

from quark.jasmin.models import JasminUser
from quark.utils.fields import InputTextWidget, NumberInputTextWidget, SelectWidget, TextareaWidget

PHONE_SPLIT_RE = re.compile(r"[\s,;]+")


class WorkspaceForm(forms.Form):
    """Non-model form with workspace injection (same pattern as BaseWorkspaceForm)."""

    def __init__(self, *args, **kwargs):
        self.workspace = kwargs.pop("workspace")
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned = super().clean()
        cleaned["workspace"] = self.workspace
        return cleaned


def normalize_msisdn(raw: str) -> str:
    value = (raw or "").strip()
    value = value.replace(" ", "").replace("-", "")
    if value.startswith("+"):
        value = value[1:]
    return value


def parse_recipients(raw: str) -> list[str]:
    """Split a bulk recipient blob into unique MSISDNs preserving order."""
    seen = set()
    recipients = []
    for part in PHONE_SPLIT_RE.split(raw or ""):
        msisdn = normalize_msisdn(part)
        if not msisdn:
            continue
        if not msisdn.isdigit() or len(msisdn) < 8 or len(msisdn) > 15:
            raise forms.ValidationError(
                f"Invalid destination number: {part!r}. Use digits only (8–15)."
            )
        if msisdn not in seen:
            seen.add(msisdn)
            recipients.append(msisdn)
    return recipients


class SendSMSForm(WorkspaceForm):
    jasmin_user = forms.ModelChoiceField(
        queryset=JasminUser.objects.none(),
        label="Send as",
        help_text="Jasmin HTTP API user (credentials synced to the gateway)",
        widget=SelectWidget(),
    )
    to_addr = forms.CharField(
        label="To",
        max_length=32,
        help_text="Destination MSISDN, digits only (country code included)",
        widget=InputTextWidget(attrs={"placeholder": "256700000001"}),
    )
    from_addr = forms.CharField(
        label="From",
        max_length=32,
        required=False,
        help_text="Optional source address / short code",
        widget=InputTextWidget(),
    )
    content = forms.CharField(
        label="Message",
        widget=TextareaWidget(attrs={"rows": 5, "placeholder": "Your SMS content…"}),
        help_text="SMS body. Keep within carrier segment limits when possible.",
    )
    dlr_level = forms.ChoiceField(
        label="DLR level",
        choices=(
            (1, "1 — SMSC delivery receipt"),
            (2, "2 — Terminal delivery receipt"),
            (3, "3 — Both (recommended)"),
        ),
        initial=3,
        widget=SelectWidget(),
    )
    priority = forms.IntegerField(
        label="Priority",
        min_value=0,
        max_value=3,
        initial=0,
        required=False,
        widget=NumberInputTextWidget(),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["jasmin_user"].queryset = JasminUser.objects.filter(
            group__workspace=self.workspace,
            enabled=True,
        ).order_by("username")
        if not self.fields["jasmin_user"].queryset.exists():
            self.fields["jasmin_user"].help_text = (
                "No enabled Jasmin users in this workspace. "
                "Enable a user under Configure → Users."
            )

    def clean_to_addr(self):
        msisdn = normalize_msisdn(self.cleaned_data.get("to_addr", ""))
        if not msisdn.isdigit() or len(msisdn) < 8 or len(msisdn) > 15:
            raise forms.ValidationError("Enter a valid destination MSISDN (8–15 digits).")
        return msisdn

    def clean_content(self):
        content = (self.cleaned_data.get("content") or "").strip()
        if not content:
            raise forms.ValidationError("Message content is required.")
        return content


class BulkSendSMSForm(WorkspaceForm):
    jasmin_user = forms.ModelChoiceField(
        queryset=JasminUser.objects.none(),
        label="Send as",
        widget=SelectWidget(),
    )
    recipients = forms.CharField(
        label="Recipients",
        widget=TextareaWidget(
            attrs={
                "rows": 8,
                "placeholder": (
                    "One number per line (or comma / semicolon separated)\n"
                    "256700000001\n256700000002"
                ),
            }
        ),
        help_text="Up to 500 destinations per batch.",
    )
    from_addr = forms.CharField(
        label="From",
        max_length=32,
        required=False,
        widget=InputTextWidget(),
    )
    content = forms.CharField(
        label="Message",
        widget=TextareaWidget(attrs={"rows": 5}),
    )
    dlr_level = forms.ChoiceField(
        label="DLR level",
        choices=((1, "1 — SMSC"), (2, "2 — Terminal"), (3, "3 — Both")),
        initial=3,
        widget=SelectWidget(),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["jasmin_user"].queryset = JasminUser.objects.filter(
            group__workspace=self.workspace,
            enabled=True,
        ).order_by("username")
        if not self.fields["jasmin_user"].queryset.exists():
            self.fields["jasmin_user"].help_text = (
                "No enabled Jasmin users in this workspace. "
                "Enable a user under Configure → Users."
            )

    def clean_recipients(self):
        recipients = parse_recipients(self.cleaned_data.get("recipients", ""))
        if not recipients:
            raise forms.ValidationError("Add at least one destination number.")
        if len(recipients) > 500:
            raise forms.ValidationError("Maximum 500 recipients per bulk send.")
        return recipients

    def clean_content(self):
        content = (self.cleaned_data.get("content") or "").strip()
        if not content:
            raise forms.ValidationError("Message content is required.")
        return content

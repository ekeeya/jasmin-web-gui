#  Copyright (c) 2025
#  File created on 2025/4/26
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
import re

from django import forms
from django.utils.text import slugify

from quark.jasmin.models import JasminGroup, JasminUser, JasminSMPPConnector, JasminFilter, JasminRoute, \
    JasminInterceptor, JasminHTTPConnector
from quark.jasmin.views.sub_forms import MessagingAuthorizationsForm, MessagingValueFiltersForm, MessagingDefaultsForm, \
    MessagingQuotasForm, SMPPAuthorizationsForm, SMPPQuotasForm
from quark.utils.fields import SelectWidget, TextareaWidget, FilePickerWidget, CheckboxInputWidget
from quark.workspace.views.forms import BaseWorkspaceForm


class JasminGroupForm(BaseWorkspaceForm):
    gid = forms.CharField(
        label="UID*",
        max_length=JasminGroup._meta.get_field("gid").max_length,
        help_text=JasminGroup._meta.get_field("gid").help_text,
        widget=forms.TextInput(attrs={
            "required": True,
            "widget_only": True,
            "placeholder": "test_group"
        }),
    )

    def clean_gid(self):
        gid = self.cleaned_data["gid"]
        prefix = f"g{self.workspace.id}"
        clean_name = f"{prefix}_{slugify(gid)}".lower()
        regex = re.compile(r'^[A-Za-z0-9_-]{1,16}$')

        if not regex.match(clean_name):
            raise forms.ValidationError(
                f"Group ID must be 1-16 characters long and contain only letters, numbers, underscores, or hyphens."
                f" Note that we also prefix it with {prefix}_"
            )

        # Check for existing group
        if JasminGroup.objects.filter(gid=clean_name).exists():
            raise forms.ValidationError(f"JasminGroup with name {gid} already exists")

        return clean_name

    def clean(self):
        self.cleaned_data['workspace'] = self.workspace
        return self.cleaned_data

    class Meta:
        model = JasminGroup
        fields = ('gid', 'description')


class UpdateJasminGroupForm(BaseWorkspaceForm):
    class Meta:
        model = JasminGroup
        fields = ('description',)  # we can only update the description


class JasminUserForm(BaseWorkspaceForm):
    enabled = forms.BooleanField(
        required=False,
        initial=True,
        label="Enabled",
        widget=CheckboxInputWidget(),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Must conform to our workspace.
        self.fields['group'].queryset = self.workspace.jasmin_groups
        # Get the data for subforms
        mt_data = self.instance.mt_credential if self.instance.pk else {}
        smpps_data = self.instance.smpps_credential if self.instance.pk else {}

        # Initialize subforms with data if this is a POST request i.e when form is bound
        if self.is_bound:
            self.mt_auth_form = MessagingAuthorizationsForm(
                data=self.data, prefix='mt_auth')
            self.mt_filter_form = MessagingValueFiltersForm(
                data=self.data, prefix='mt_filter')
            self.mt_default_form = MessagingDefaultsForm(
                data=self.data, prefix='mt_default')
            self.mt_quota_form = MessagingQuotasForm(
                data=self.data, prefix='mt_quota')

            self.smpps_auth_form = SMPPAuthorizationsForm(
                data=self.data, prefix='smpps_auth')
            self.smpps_quota_form = SMPPQuotasForm(
                data=self.data, prefix='smpps_quota')
        else:
            # For GET requests, use initial data
            self.mt_auth_form = MessagingAuthorizationsForm(
                initial=mt_data.get('authorizations', {}), prefix='mt_auth')
            self.mt_filter_form = MessagingValueFiltersForm(
                initial=mt_data.get('value_filters', {}), prefix='mt_filter')
            self.mt_default_form = MessagingDefaultsForm(
                initial=mt_data.get('defaults', {}), prefix='mt_default')
            self.mt_quota_form = MessagingQuotasForm(
                initial=mt_data.get('quotas', {}), prefix='mt_quota')

            self.smpps_auth_form = SMPPAuthorizationsForm(
                initial=smpps_data.get('authorizations', {}), prefix='smpps_auth')
            self.smpps_quota_form = SMPPQuotasForm(
                initial=smpps_data.get('quotas', {}), prefix='smpps_quota')

    def clean(self):
        cleaned_data = super().clean()

        # Validate mt_credentials subforms
        mt_forms = [
            (self.mt_auth_form, 'Messaging Authorizations'),
            (self.mt_filter_form, 'Messaging Value Filters'),
            # (self.mt_default_form, 'Messaging Defaults'),
            (self.mt_quota_form, 'Messaging Quotas'),
        ]
        for form, label in mt_forms:
            if not form.is_valid():
                errors = []
                for field, field_errors in form.errors.items():
                    for error in field_errors:
                        errors.append(f"{field}: {error}")
                raise forms.ValidationError(f"Invalid {label}: {', '.join(errors)}")

        # Validate smpps_credential subforms
        smpps_forms = [
            (self.smpps_auth_form, 'SMPP Authorizations'),
            (self.smpps_quota_form, 'SMPP Quotas'),
        ]
        for form, label in smpps_forms:
            if not form.is_valid():
                errors = []
                for field, field_errors in form.errors.items():
                    for error in field_errors:
                        errors.append(f"{field}: {error}")
                raise forms.ValidationError(f"Invalid {label}: {', '.join(errors)}")

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        # Construct mt_credential
        instance.mt_credential = {
            'authorizations': self.mt_auth_form.cleaned_data,
            'value_filters': self.mt_filter_form.cleaned_data,
            # 'defaults': self.mt_default_form.cleaned_data,
            'quotas': self.mt_quota_form.cleaned_data,
        }

        # Construct smpps_credential
        instance.smpps_credential = {
            'authorizations': self.smpps_auth_form.cleaned_data,
            'quotas': self.smpps_quota_form.cleaned_data,
        }

        if commit:
            instance.save()
        return instance

    class Meta:
        model = JasminUser
        # mt_credential / smpps_credential are assembled from subforms in save()
        fields = ('username', 'password', 'group', 'enabled')


class JasminSPPConnectorForm(BaseWorkspaceForm):

    def clean(self):
        self.cleaned_data['workspace'] = self.workspace
        log_file = self.cleaned_data['log_file']
        if log_file == '':
            # if log file is not set leave it upto jasmin to default it
            del self.cleaned_data['log_file']
        return self.cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)

        # add workspace to instance
        instance.workspace = self.cleaned_data['workspace']

        if commit:
            instance.save()
        return instance

    class Meta:
        model = JasminSMPPConnector
        exclude = ("cid", "workspace", "connector_type", "created_by", 'modified_by')


class JasminHttpConnectorForm(BaseWorkspaceForm):

    def save(self, commit=True):
        instance = super().save(commit=False)

        # add workspace to instance
        instance.workspace = self.cleaned_data['workspace']

        if commit:
            instance.save()
        return instance

    class Meta:
        model = JasminHTTPConnector
        exclude = ("cid", "workspace", "connector_type", "created_by", 'modified_by', 'is_active')


class JasminFilterForm(BaseWorkspaceForm):
    # Add these fields for the JSON param input
    param_key = forms.CharField(
        required=False,
        label="Parameter Key",
        initial=None,
        help_text="Enter the parameter key (EvalPyFilter uses pyCode)",
    )
    param_value = forms.CharField(
        required=False,
        initial=None,
        label="Parameter Value",
        help_text="Enter the parameter value. For EvalPyFilter, paste Python source here.",
        widget=TextareaWidget(attrs={
            "class": "param-value-input",
            "rows": 3,
            "placeholder": "Parameter value",
        }),
    )
    script_file = forms.FileField(
        required=False,
        label="Upload script (optional)",
        help_text="Optional .py file. Contents are copied into Parameter Value (EvalPyFilter).",
        widget=FilePickerWidget(attrs={"accept": ".py,text/x-python"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # If we're editing an existing instance, pre-populate the param fields
        if self.instance and self.instance.param:
            self.fields['param_key'].initial = self.instance.param.get('key', '')
            self.fields['param_value'].initial = self.instance.param.get('value', '')

    def clean_script_file(self):
        uploaded = self.cleaned_data.get("script_file")
        if uploaded and not uploaded.name.lower().endswith(".py"):
            raise forms.ValidationError("Uploaded script must be a .py file")
        return uploaded

    def clean(self):
        cleaned_data = super().clean()
        cleaned_data['workspace'] = self.workspace

        filter_type = cleaned_data.get("filter_type")
        param_key = (cleaned_data.get("param_key") or "").strip()
        param_value = cleaned_data.get("param_value")
        uploaded = cleaned_data.get("script_file")

        if uploaded and filter_type == "EvalPyFilter":
            raw = uploaded.read()
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8")
            param_value = raw
            if hasattr(uploaded, "seek"):
                uploaded.seek(0)
            cleaned_data["param_key"] = "pyCode"
            param_key = "pyCode"

        if isinstance(param_value, str):
            # Keep EvalPy source as-stripped for storage; other params strip lightly
            if filter_type == "EvalPyFilter":
                param_value = param_value.strip()
            else:
                param_value = param_value.strip() if param_value else param_value

        cleaned_data["param_key"] = param_key or None
        cleaned_data["param_value"] = param_value or None

        param_key = cleaned_data.get("param_key")
        param_value = cleaned_data.get("param_value")

        if filter_type == "EvalPyFilter":
            if param_key and param_key != "pyCode":
                self.add_error("param_key", "EvalPyFilter parameter key must be pyCode")
            cleaned_data["param_key"] = "pyCode"
            if not param_value:
                self.add_error(
                    "param_value",
                    "Provide Python source, or upload a .py file to fill it",
                )
            else:
                try:
                    compile(param_value, "<EvalPyFilter>", "exec")
                except SyntaxError as exc:
                    self.add_error("param_value", f"Script has a syntax error: {exc}")
                else:
                    cleaned_data["param_value"] = param_value
        elif bool(param_key) != bool(param_value):
            raise forms.ValidationError(
                "Both parameter key and value must be provided together or left blank"
            )

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)

        # Construct the param JSON from the form inputs
        param_key = self.cleaned_data.get('param_key')
        param_value = self.cleaned_data.get('param_value')

        if param_key and param_value is not None and param_value != "":
            instance.param = {'key': param_key, 'value': param_value}
        else:
            instance.param = None

        # add workspace to instance
        instance.workspace = self.cleaned_data['workspace']

        if commit:
            instance.save()
        return instance

    class Meta:
        model = JasminFilter
        exclude = ("workspace", "is_active", "created_by", 'modified_by', 'param')
        widgets = {
            'filter_type': SelectWidget(),
        }


class JasminRouteForm(BaseWorkspaceForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Must conform to our workspace.
        self.fields['filters'].queryset = JasminFilter.objects.filter(workspace=self.workspace)
        self.fields['smpp_connectors'].queryset = JasminSMPPConnector.objects.filter(workspace=self.workspace)
        self.fields['http_connectors'].queryset = JasminHTTPConnector.objects.filter(workspace=self.workspace)
        # un mandatory these connectors
        self.fields['filters'].required = False
        self.fields['smpp_connectors'].required = False
        self.fields['http_connectors'].required = False

    def save(self, commit=True):
        instance = super().save(commit=False)
        # add workspace to instance
        instance.workspace = self.cleaned_data['workspace']

        if commit:
            instance.save()
        return instance

    class Meta:
        model = JasminRoute
        fields = ("nature", "router_type", "order", "filters", "smpp_connectors", "http_connectors", "rate")


class JasminInterceptorForm(BaseWorkspaceForm):
    """
    Create form for MO/MT interceptors.

    Script source of truth is stored in the DB (`script_source`). An optional
    .py upload can prefill that textarea in the browser / on submit.
    """
    script_file = forms.FileField(
        required=False,
        label="Upload script (optional)",
        help_text="Optional .py file. Its contents are copied into Script source below.",
        widget=forms.ClearableFileInput(attrs={"accept": ".py,text/x-python"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["filters"].queryset = JasminFilter.objects.filter(workspace=self.workspace)
        self.fields["filters"].required = False
        self.fields["filters"].help_text = (
            "Required for StaticMO/StaticMTInterceptor. Leave empty for DefaultInterceptor."
        )
        self.fields["script_source"].help_text = (
            "Python 3 source stored in Joyce's database and sent to Jasmin as pyCode. "
            "Re-save the interceptor after editing to refresh Jasmin's copy."
        )
        self.fields["script_source"].widget = TextareaWidget(attrs={
            "rows": 12,
            "placeholder": "# result = True  to accept / continue\n# result = False to reject\nresult = True\n",
        })
        self.fields["script_file"].widget = FilePickerWidget(attrs={
            "accept": ".py,text/x-python",
        })
        self.fields["script_name"].required = False
        self.fields["script_name"].help_text = "Optional label (auto-filled from an uploaded filename)."
        self.fields["order"].required = False
        self.fields["order"].help_text = (
            "Unique order within this workspace and nature. "
            "DefaultInterceptor is always order 0."
        )

    def clean_script_file(self):
        uploaded = self.cleaned_data.get("script_file")
        if uploaded and not uploaded.name.lower().endswith(".py"):
            raise forms.ValidationError("Uploaded script must be a .py file")
        return uploaded

    def clean_script_source(self):
        source = (self.cleaned_data.get("script_source") or "").strip()
        return source

    def clean(self):
        cleaned_data = super().clean()
        cleaned_data["workspace"] = self.workspace

        nature = cleaned_data.get("nature")
        interceptor_type = cleaned_data.get("interceptor_type")
        filters = cleaned_data.get("filters")
        order = cleaned_data.get("order")
        uploaded = cleaned_data.get("script_file")
        source = (cleaned_data.get("script_source") or "").strip()

        if uploaded:
            raw = uploaded.read()
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8")
            source = raw.strip()
            if hasattr(uploaded, "seek"):
                uploaded.seek(0)
            if not cleaned_data.get("script_name"):
                cleaned_data["script_name"] = uploaded.name.rsplit("/", 1)[-1]

        if not source:
            self.add_error(
                "script_source",
                "Provide script source, or upload a .py file to fill it",
            )
        else:
            filename = cleaned_data.get("script_name") or "<interceptor>"
            try:
                compile(source, filename, "exec")
            except SyntaxError as exc:
                self.add_error("script_source", f"Script has a syntax error: {exc}")
            else:
                cleaned_data["script_source"] = source

        if not nature or not interceptor_type:
            return cleaned_data

        if interceptor_type == "StaticMOInterceptor" and nature != "MO":
            raise forms.ValidationError(
                "StaticMOInterceptor can only be used with nature MO"
            )
        if interceptor_type == "StaticMTInterceptor" and nature != "MT":
            raise forms.ValidationError(
                "StaticMTInterceptor can only be used with nature MT"
            )

        if interceptor_type == "DefaultInterceptor":
            cleaned_data["order"] = 0
            if filters and filters.exists():
                raise forms.ValidationError(
                    "DefaultInterceptor does not accept filters "
                    "(it is the fallback interceptor at order 0)"
                )
            cleaned_data["filters"] = JasminFilter.objects.none()
        else:
            if order is None:
                self.add_error("order", "Order is required for Static interceptors")
            elif order == 0:
                self.add_error(
                    "order",
                    "Order 0 is reserved for DefaultInterceptor",
                )
            if not filters or not filters.exists():
                self.add_error(
                    "filters",
                    f"{interceptor_type} requires at least one filter",
                )
            elif filters:
                incompatible = filters.exclude(nature__in=[nature, "ALL"])
                if incompatible.exists():
                    fids = ", ".join(incompatible.values_list("fid", flat=True))
                    self.add_error(
                        "filters",
                        f"These filters are not compatible with {nature} interceptors: {fids}",
                    )

        final_order = cleaned_data.get("order")
        if nature is not None and final_order is not None:
            qs = JasminInterceptor.objects.filter(
                workspace=self.workspace,
                nature=nature,
                order=final_order,
            )
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                self.add_error(
                    "order",
                    f"An interceptor with order {final_order} already exists "
                    f"for {nature} in this workspace",
                )

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.workspace = self.cleaned_data["workspace"]
        if commit:
            instance.save()
        return instance

    class Meta:
        model = JasminInterceptor
        fields = (
            "nature",
            "interceptor_type",
            "order",
            "filters",
            "script_name",
            "script_source",
        )

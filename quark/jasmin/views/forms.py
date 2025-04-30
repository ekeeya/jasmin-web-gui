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

from quark.jasmin.models import JasminGroup, JasminUser, JasminSMPPConnector
from quark.jasmin.views.sub_forms import MessagingAuthorizationsForm, MessagingValueFiltersForm, MessagingDefaultsForm, \
    MessagingQuotasForm, SMPPAuthorizationsForm, SMPPQuotasForm


class JasminGroupForm(forms.ModelForm):
    gid = forms.CharField(
        label="Group ID*",
        max_length=JasminGroup._meta.get_field("gid").max_length,
        help_text=JasminGroup._meta.get_field("gid").help_text,
        widget=forms.TextInput(attrs={
            "required": True,
            "widget_only": True,
            "placeholder": "test_group"
        }),
    )

    def __init__(self, *args, **kwargs):
        # Inject the workspace
        self.workspace = kwargs["workspace"]
        del kwargs["workspace"]
        super().__init__(*args, **kwargs)

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


class UpdateJasminGroupForm(forms.ModelForm):
    def __init__(self, workspace, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.workspace = workspace

    class Meta:
        model = JasminGroup
        fields = ('description',)  # we can only update the description


class JasminUserForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        # Inject the workspace
        self.workspace = kwargs["workspace"]
        del kwargs["workspace"]
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
        fields = ('username', 'password', 'group', 'mt_credential', 'smpps_credential')


class JasminSPPConnectorForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        # Inject the workspace
        self.workspace = kwargs["workspace"]
        del kwargs["workspace"]
        super().__init__(*args, **kwargs)

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
        exclude = ("cid","workspace")

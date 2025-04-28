#  Copyright (c) 2025
#  File created on 2025/4/28
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


# Jasmin user subforms
class MessagingAuthorizationsForm(forms.Form):
    http_send = forms.BooleanField(
        required=False, label="HTTP Send", initial=True)
    http_balance = forms.BooleanField(
        required=False, label="HTTP Balance", initial=True)
    http_rate = forms.BooleanField(
        required=False, label="HTTP Rate", initial=True)
    http_bulk = forms.BooleanField(
        required=False, label="HTTP Bulk", initial=False)
    smpps_send = forms.BooleanField(
        required=False, label="SMPPS Send", initial=True)
    http_long_content = forms.BooleanField(
        required=False, label="HTTP Long Content", initial=True)
    set_dlr_level = forms.BooleanField(
        required=False, label="Set DLR Level", initial=True)
    http_set_dlr_method = forms.BooleanField(
        required=False, label="HTTP Set DLR Method", initial=True)
    set_source_address = forms.BooleanField(
        required=False, label="Set Source Address", initial=True)
    set_priority = forms.BooleanField(
        required=False, label="Set Priority", initial=True)
    set_validity_period = forms.BooleanField(
        required=False, label="Set Validity Period", initial=True)
    set_schedule_delivery_time = forms.BooleanField(
        required=False, label="Set Schedule Delivery Time", initial=True)
    set_hex_content = forms.BooleanField(
        required=False, label="Set Hex Content", initial=True)


class MessagingValueFiltersForm(forms.Form):
    destination_address = forms.CharField(required=False, label="Destination Address", initial=".*")
    source_address = forms.CharField(required=False, label="Source Address", initial=".*")
    priority = forms.CharField(required=False, label="Priority", initial="^[0-3]$")
    validity_period = forms.CharField(required=False, label="Validity Period", initial="^\d+$")
    content = forms.CharField(required=False, label="Content", initial=".*")


class MessagingDefaultsForm(forms.Form):
    source_address = forms.CharField(required=False, label="Source Address", empty_value=None)


class MessagingQuotasForm(forms.Form):
    balance = forms.IntegerField(
        required=False,
        label="Balance",
        initial=None,
        widget=forms.NumberInput(attrs={'placeholder': 'Enter integer or leave blank'})
    )
    early_decrement_balance_percent = forms.IntegerField(
        required=False,
        label="Early Percent",
        initial=None,
        widget=forms.NumberInput(attrs={'placeholder': 'Enter integer or leave blank'})
    )
    submit_sm_count = forms.IntegerField(
        required=False,
        label="SMS Count",
        initial=None,
        widget=forms.NumberInput(attrs={'placeholder': 'Enter integer or leave blank'})
    )
    http_throughput = forms.IntegerField(
        required=False,
        label="HTTP Throughput",
        initial=None,
        widget=forms.NumberInput(attrs={'placeholder': 'Enter integer or leave blank'})
    )
    smpps_throughput = forms.IntegerField(
        required=False,
        label="SMPPS Throughput",
        initial=None,
        widget=forms.NumberInput(attrs={'placeholder': 'Enter integer or leave blank'})
    )

    def clean(self):
        cleaned_data = super().clean()

        # Convert empty string values to None
        for field in self.fields:
            if field in cleaned_data and cleaned_data[field] == '':
                cleaned_data[field] = None
        return cleaned_data


class SMPPAuthorizationsForm(forms.Form):
    bind = forms.BooleanField(required=False, label="Bind", initial=True)


class SMPPQuotasForm(forms.Form):
    max_bindings = forms.IntegerField(
        required=False,
        label="Max Bindings",
        initial=None,
        widget=forms.NumberInput(attrs={'placeholder': 'Enter integer or leave blank'})
    )

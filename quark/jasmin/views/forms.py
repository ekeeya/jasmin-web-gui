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

from quark.jasmin.models import JasminGroup


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

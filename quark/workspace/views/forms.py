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
from django.contrib.auth.password_validation import validate_password
from django_countries.fields import CountryField
from timezone_field import TimeZoneFormField

from quark.workspace.models import User, WorkSpace


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

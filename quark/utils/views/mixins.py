#  Copyright (c) 2025
#  File created on 2025/5/8
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

from quark.utils.fields import (
    InputTextWidget, CheckboxInputWidget, SelectWidget, MultiSelectWidget, FilePickerWidget, TextareaWidget
)


class FormMixin:
    """
    Mixin to replace form field controls with component based widgets
    """

    def customize_form_field(self, name, field):
        attrs = field.widget.attrs if field.widget.attrs else {}

        # Don't replace the widget if it is already one of our custom widgets
        if isinstance(
            field.widget,
            (
                forms.widgets.HiddenInput,
                CheckboxInputWidget,
                InputTextWidget,
                SelectWidget,
                MultiSelectWidget,
                FilePickerWidget,
                TextareaWidget,  # Added TextareaWidget to the check
            ),
        ):
            return field

        # Replace standard widgets with our custom widgets
        if isinstance(field.widget, (forms.widgets.Textarea,)):
            field.widget = TextareaWidget(attrs=attrs)
        elif isinstance(field.widget, (forms.widgets.PasswordInput,)):
            attrs["password"] = True
            field.widget = InputTextWidget(attrs=attrs)
        elif isinstance(
            field.widget,
            (
                forms.widgets.TextInput,
                forms.widgets.EmailInput,
                forms.widgets.URLInput,
                forms.widgets.NumberInput,
            ),
        ):
            field.widget = InputTextWidget(attrs=attrs)
        elif isinstance(field.widget, (forms.widgets.Select,)):
            if isinstance(field, (forms.models.ModelMultipleChoiceField,)):
                field.widget = MultiSelectWidget(attrs)  # pragma: needs cover
            else:
                field.widget = SelectWidget(attrs)

            field.widget.choices = field.choices
        elif isinstance(field.widget, (forms.widgets.CheckboxInput,)):
            field.widget = CheckboxInputWidget(attrs)
        elif isinstance(field.widget, (forms.widgets.FileInput,)):
            field.widget = FilePickerWidget(attrs=attrs)

        return field

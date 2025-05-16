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
from django.urls import reverse

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
            default_attrs = {"cols": "5", "rows": "2"}
            attrs.update(default_attrs)
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


class InjectModalFormMixin(FormMixin):
    """
    Mixin to inject a form in a list's context
    """
    modal_form = None
    post_url = None
    display_field = "id"
    name = None
    actions = ["edit", "delete"]
    update_form = None

    def update_form_use_tailwind(self, form):
        for name, field in form.fields.items():
            field = self.customize_form_field(name, field)
            form.fields[name] = field
        return form

    class Modal:
        """Will represent a modal """

        def __init__(self, form, customize_form_field):
            self.modal = dict()
            self.form = form
            self.customize_form_field = customize_form_field

        def to_tailwind(self):
            # apply our tailwind widget from FormMixin
            for name, field in self.form.fields.items():
                field = self.customize_form_field(name, field)
                self.form.fields[name] = field

        def register_modal(self, title: str, modal_id: str, post_url: str, custom_form: str = None):
            self.to_tailwind()
            self.modal = dict(
                title=title,
                modal_id=modal_id,
                post_url=post_url,
                form=self.form
            )
            if custom_form:
                self.modal["custom_form"] = custom_form

    def build_update(self):
        pass

    def set_update_form_params(self, **kwargs):
        for key, value in kwargs.items():
            if key in ['post_url', 'display_field', 'name', 'modal_id']:
                setattr(self, key, value)

    def build_update_forms(self, workspace, items):
        self.build_update()
        update_forms = []
        if self.update_form:
            for item in items:
                form = self.update_form(instance=item, workspace=workspace)
                # convert to tailwind widgets
                form = self.update_form_use_tailwind(form)
                update_url = reverse(self.post_url, args=[item.id])
                data = dict(
                    id=item.id,
                    form=form,
                    post_url=update_url,
                    title=f"Update {self.name} {getattr(item, self.display_field)}")
                update_forms.append(data)
        return update_forms

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        workspace = self.derive_workspace()
        self.modal_form = self.modal_form(workspace=workspace)
        context['workspace'] = workspace  # inject the workspace too as added bonus
        # init it no going back at this level
        context['modal'] = self._get_context_modal()
        # add update forms to our list page
        context['update_forms'] = self.build_update_forms(workspace, context['object_list'])
        context["actions"] = self.actions
        return context

    def _get_context_modal(self):
        modal = self.Modal(self.modal_form, self.customize_form_field)
        self.build_modal(modal)
        return modal.modal

    def build_modal(self, modal: Modal):
        pass

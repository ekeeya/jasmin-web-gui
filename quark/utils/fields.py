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

import os
import uuid

from django.forms import widgets
from django.utils.deconstruct import deconstructible


@deconstructible
class UploadToIdPathAndRename:

    def __init__(self, path):
        self.sub_path = path

    def __call__(self, instance, filename):
        ext = filename.split('.')[-1]
        filename = '{}.{}'.format(uuid.uuid4(), ext)
        return os.path.join(self.sub_path, instance.id, filename)


class JoyceWidgetMixin:
    is_annotated = True

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        context["widget"]["type"] = self.input_type

        if attrs.get("hide_label", False) and context.get("label", None):
            del context["label"]
        return context


class TextareaWidget(widgets.Textarea):

    template_name = 'widgets/textarea.html'
    is_annotated = True


class InputTextWidget(JoyceWidgetMixin, widgets.Input):
    template_name = 'widgets/input.html'
    input_type = 'text'
    is_annotated = True


class NumberInputTextWidget(InputTextWidget):
    input_type = 'number'
    template_name = 'widgets/number_input.html'


class FilePickerWidget(JoyceWidgetMixin, widgets.ClearableFileInput):
    template_name = 'widgets/file_picker.html'


class CheckboxInputWidget(JoyceWidgetMixin, widgets.CheckboxInput):
    template_name = 'widgets/checkbox.html'
    is_annotated = True


class RadioSelectWidget(widgets.RadioSelect):
    template_name = 'widgets/radiobutton.html'
    option_template_name = 'widgets/radio_option.html'


class SelectWidget(widgets.Select):
    template_name = 'widgets/select.html'
    is_annotated = True
    # option_inherits_attrs = False


class MultiSelectWidget(widgets.SelectMultiple):
    template_name = 'widgets/multi_select.html'
    allow_multiple_selected = True

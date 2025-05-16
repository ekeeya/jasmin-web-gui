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
from django.core.paginator import Paginator
from django.urls import reverse
from smartmin.mixins import NonAtomicMixin
from smartmin.views import SmartCRUDL, SmartCreateView, SmartListView, SmartUpdateView, SmartDeleteView, \
    SmartModelActionView, SmartFormView

from quark.jasmin.models import JasminGroup, JasminUser, JasminSMPPConnector, JasminFilter, JasminRoute, \
    JasminInterceptor, JasminHTTPConnector
from django import forms
from quark.jasmin.views.forms import JasminGroupForm, UpdateJasminGroupForm, JasminUserForm, JasminSPPConnectorForm, \
    JasminFilterForm, JasminRouteForm, JasminInterceptorForm, JasminHttpConnectorForm
from quark.utils.mixins.mixins import ModalFormMixin
from quark.utils.views.mixins import FormMixin, InjectModalFormMixin
from quark.workspace.views.base import BaseListView
from quark.workspace.views.mixins import WorkspacePermsMixin


class JasminGroupCRUDL(SmartCRUDL):
    model = JasminGroup
    actions = ("create", "list", "update", "delete",)

    class Create(FormMixin, ModalFormMixin, WorkspacePermsMixin, NonAtomicMixin, SmartCreateView):
        title = "New Jasmin Group"
        form_class = JasminGroupForm
        permission = "jasmin.jasmingroup_create"
        success_url = "@jasmin.jasmingroup_list"

        def get_form_kwargs(self):
            kwargs = super().get_form_kwargs()
            kwargs["workspace"] = self.derive_workspace()
            return kwargs

        def get_context_data(self, **kwargs):
            context = super().get_context_data(**kwargs)
            workspace = self.derive_workspace()
            context["workspace"] = workspace
            return context

        def form_valid(self, form):
            self.object = JasminGroup.create(
                form.cleaned_data["gid"],
                self.request.user,
                form.cleaned_data["workspace"],
                form.cleaned_data["description"],
            )
            form.instance.pk = self.object.pk  # set it so we skip re-saving it in mixin form_valid
            return super().form_valid(form)

    class List(InjectModalFormMixin, BaseListView):
        title = "Jasmin Groups"
        ordering = ("-created_on",)
        permission = "jasmin.jasmingroup_list"
        paginate_by = 10
        template_name = "jasmin/group_list.html"
        fields = ("gid", "created_on", "description",)
        search_fields = ("gid",)
        modal_form = JasminGroupForm
        update_form = UpdateJasminGroupForm

        def build_update(self):
            self.set_update_form_params(
                post_url="jasmin.jasmingroup_update",
                name="Jasmin Group",
                display_field="gid")

        def build_modal(self, modal):
            modal.register_modal(
                title="Create a Jasmin Group",
                modal_id="jasmin_modal",
                post_url=reverse("jasmin.jasmingroup_create")
            )

        def get_context_data(self, **kwargs):
            context = super().get_context_data(**kwargs)
            # set delete url
            context["delete_url"] = "jasmin.jasmingroup_delete"
            return context

    class Update(FormMixin, ModalFormMixin, WorkspacePermsMixin, SmartUpdateView):
        title = "Update Jasmin Group"
        form_class = UpdateJasminGroupForm
        permission = "jasmin.jasmingroup_update"
        exclude = ("gid", "created_by", "modified_by",)

        success_url = "@jasmin.jasmingroup_list"

        def get_form_kwargs(self):
            kwargs = super().get_form_kwargs()
            kwargs["workspace"] = self.derive_workspace()
            return kwargs

        def save(self, obj):
            return super().save(obj)

    class Delete(WorkspacePermsMixin, NonAtomicMixin, SmartDeleteView):
        permission = "jasmin.jasmingroup_delete"
        redirect_url = "@jasmin.jasmingroup_list"
        cancel_url = "@jasmin.jasmingroup_list"


class JasminUserCRUDL(SmartCRUDL):
    actions = ("create", "list", "update", "delete",)
    model = JasminUser

    class Create(FormMixin, ModalFormMixin, WorkspacePermsMixin, NonAtomicMixin, SmartCreateView):
        permission = "jasmin.jasminuser_create"
        form_class = JasminUserForm

        def get_form_kwargs(self):
            kwargs = super().get_form_kwargs()
            kwargs["workspace"] = self.derive_workspace()
            return kwargs

    class Update(FormMixin, ModalFormMixin, WorkspacePermsMixin, NonAtomicMixin, SmartUpdateView):
        permission = "jasmin.jasminuser_update"
        form_class = JasminUserForm

        def get_form_kwargs(self):
            kwargs = super().get_form_kwargs()
            kwargs["workspace"] = self.derive_workspace()
            return kwargs

    class List(InjectModalFormMixin, BaseListView):
        permission = "jasmin.jasminuser_list"
        fields = ("username", "group", 'enabled', 'created_on')
        template_name = "jasmin/user_list.html"

        title = "Jasmin Groups"
        ordering = ("-created_on",)
        paginate_by = 10
        search_fields = ("gid",)
        modal_form = JasminUserForm
        update_form = JasminUserForm

        def build_update(self):
            self.set_update_form_params(
                post_url="jasmin.jasminuser_update",
                name="Jasmin User",
                display_field="username")

        def build_modal(self, modal):
            modal.register_modal(
                title="Create a Jasmin User",
                modal_id="jasmin_user",
                post_url=reverse("jasmin.jasminuser_create"),
                custom_form="jasmin/user_create.html",
            )

        def get_context_data(self, **kwargs):
            context = super().get_context_data(**kwargs)
            # set delete url
            context["delete_url"] = "jasmin.jasminuser_delete"
            return context

    class Delete(WorkspacePermsMixin, NonAtomicMixin, SmartDeleteView):
        permission = "jasmin.jasminuser_delete"
        redirect_url = "@jasmin.jasminuser_list"
        cancel_url = "@jasmin.jasminuser_list"


class JasminSMPPConnectorCRUDL(SmartCRUDL):
    actions = ("configure", "list", "update", "delete", "start", "stop")
    model = JasminSMPPConnector

    class Start(WorkspacePermsMixin, SmartFormView, SmartModelActionView):
        class StartForm(forms.Form):
            pass

        permission = "jasmin.jasmin_smpp_connector_start"
        success_url = "@jasmin.jasminsmppconnector_list"
        slug_url_kwarg = "id"
        form_class = StartForm

        def execute_action(self):
            # start the connector on jasmin
            self.object.start()

    class Stop(WorkspacePermsMixin, SmartFormView, SmartModelActionView):
        class StopForm(forms.Form):
            pass

        permission = "jasmin.jasmin_smpp_connector_stop"
        success_url = "@jasmin.jasminsmppconnector_list"
        slug_url_kwarg = "id"
        form_class = StopForm

        def execute_action(self):
            # stop the connector on jasmin
            self.object.stop()

    class Configure(FormMixin, ModalFormMixin, WorkspacePermsMixin, NonAtomicMixin, SmartCreateView):
        title = "Configure SMPP Connector"
        permission = "jasmin.jasminsmppconnector_configure"
        form_class = JasminSPPConnectorForm
        success_url = "@jasmin.jasminsmppconnector_list"

        def get_form_kwargs(self):
            kwargs = super().get_form_kwargs()
            kwargs["workspace"] = self.derive_workspace()
            return kwargs

    class Update(FormMixin, ModalFormMixin, WorkspacePermsMixin, NonAtomicMixin, SmartUpdateView):
        permission = "jasmin.jasminsmppconnector_update"
        form_class = JasminSPPConnectorForm

        def get_form_kwargs(self):
            kwargs = super().get_form_kwargs()
            kwargs["workspace"] = self.derive_workspace()
            return kwargs

    class List(InjectModalFormMixin, BaseListView):
        title = "SMPP SMPP Connectors"
        permission = "jasmin.jasminsmppconnector_list"
        paginator_class = Paginator
        paginate_by = 10
        fields = ("cid", "host", "port", 'created_on')
        template_name = "jasmin/smpp_connectors.html"
        ordering = ("-created_on",)
        search_fields = ("cid",)
        modal_form = JasminSPPConnectorForm
        update_form = JasminSPPConnectorForm
        actions = ['status', 'edit', 'delete']

        def build_update(self):
            self.set_update_form_params(
                post_url="jasmin.jasminsmppconnector_update",
                name="Connector",
                display_field="cid")

        def build_modal(self, modal):
            modal.register_modal(
                title="Configure Connector",
                modal_id="jasmin_connector",
                post_url=reverse("jasmin.jasminsmppconnector_configure")
            )

        def get_context_data(self, **kwargs):
            context = super().get_context_data(**kwargs)
            # set delete url
            context["delete_url"] = "jasmin.jasminsmppconnector_delete"
            return context

    class Delete(WorkspacePermsMixin, NonAtomicMixin, SmartDeleteView):
        permission = "jasmin.jasminsmppconnector_delete"
        redirect_url = "@jasmin.jasminsmppconnector_list"
        cancel_url = "@jasmin.jasminsmppconnector_list"


class JasminHTTPConnectorCRUDL(SmartCRUDL):
    actions = ("configure", "list", "update", "delete",)
    model = JasminHTTPConnector

    class Configure(FormMixin, ModalFormMixin, WorkspacePermsMixin, NonAtomicMixin, SmartCreateView):
        title = "Configure HTTP Connector"
        permission = "jasmin.jasminhttpconnector_configure"
        form_class = JasminHttpConnectorForm
        success_url = "@jasmin.jasminhttpconnector_list"

        def get_form_kwargs(self):
            kwargs = super().get_form_kwargs()
            kwargs["workspace"] = self.derive_workspace()
            return kwargs

    class Update(FormMixin, ModalFormMixin, WorkspacePermsMixin, NonAtomicMixin, SmartUpdateView):
        permission = "jasmin.jasminhttpconnector_update"
        form_class = JasminHttpConnectorForm

        def get_form_kwargs(self):
            kwargs = super().get_form_kwargs()
            kwargs["workspace"] = self.derive_workspace()
            return kwargs

    class List(InjectModalFormMixin, BaseListView):
        title = "HTTP Connectors"
        permission = "jasmin.jasminhttpconnector_list"
        paginator_class = Paginator
        paginate_by = 10
        fields = ("cid", "base_url", "method", 'created_on')
        template_name = "jasmin/http_connectors.html"
        ordering = ("-created_on",)
        search_fields = ("cid",)
        modal_form = JasminHttpConnectorForm
        update_form = JasminHttpConnectorForm
        actions = ['edit', 'delete']

        def build_update(self):
            self.set_update_form_params(
                post_url="jasmin.jasminhttpconnector_update",
                name="Connector",
                display_field="cid")

        def build_modal(self, modal):
            modal.register_modal(
                title="Configure HTTP Connector",
                modal_id="jasmin_connector",
                post_url=reverse("jasmin.jasminhttpconnector_configure")
            )

        def get_context_data(self, **kwargs):
            context = super().get_context_data(**kwargs)
            # set delete url
            context["delete_url"] = "jasmin.jasminhttpconnector_delete"
            return context

    class Delete(WorkspacePermsMixin, NonAtomicMixin, SmartDeleteView):
        permission = "jasmin.jasminhttpconnector_delete"
        redirect_url = "@jasmin.jasminhttpconnector_list"
        cancel_url = "@jasmin.jasminhttpconnector_list"


class JasminFilterCRUDL(SmartCRUDL):
    actions = ("create", "list", "delete",)
    model = JasminFilter

    class Create(FormMixin, ModalFormMixin, WorkspacePermsMixin, NonAtomicMixin, SmartCreateView):
        title = "Create Message Filter"
        permission = "jasmin.jasminfilter_create"
        form_class = JasminFilterForm
        success_url = "@jasmin.jasminfilter_list"

        def get_form_kwargs(self):
            kwargs = super().get_form_kwargs()
            kwargs["workspace"] = self.derive_workspace()
            return kwargs

    class List(InjectModalFormMixin, BaseListView):
        title = "Message Filters"
        permission = "jasmin.jasminfilter_list"
        paginator_class = Paginator
        paginate_by = 10
        fields = ("fid", "nature", "filter_type", "param", 'created_on')
        template_name = "jasmin/filters.html"
        ordering = ("-created_on",)
        search_fields = ("fid",)
        modal_form = JasminFilterForm
        actions = ['delete']

        def build_modal(self, modal):
            modal.register_modal(
                title="Configure a Filter",
                modal_id="jasmin_filter",
                post_url=reverse("jasmin.jasminfilter_create"),
                custom_form="jasmin/filter_create.html"
            )

        def get_context_data(self, **kwargs):
            context = super().get_context_data(**kwargs)
            # set delete url
            context["delete_url"] = "jasmin.jasminfilter_delete"
            return context

    class Delete(WorkspacePermsMixin, NonAtomicMixin, SmartDeleteView):
        permission = "jasmin.jasminfilter_delete"
        redirect_url = "@jasmin.jasminfilter_list"
        cancel_url = "@jasmin.jasminfilter_list"


class JasminRouteCRUDL(SmartCRUDL):
    actions = ("create", "list", "update", "delete",)
    model = JasminRoute

    class Create(FormMixin, WorkspacePermsMixin, NonAtomicMixin, SmartCreateView):
        title = "Create Route"
        permission = "jasmin.jasminroute_create"
        form_class = JasminRouteForm
        success_url = "@jasmin.jasminroute_list"

        def get_form_kwargs(self):
            kwargs = super().get_form_kwargs()
            kwargs["workspace"] = self.derive_workspace()
            return kwargs

        def save(self, obj):
            route = JasminRoute(
                router_type=self.form.cleaned_data["router_type"],
                nature=self.form.cleaned_data["nature"],
                workspace=self.derive_workspace(),
                order=self.form.cleaned_data["order"],
                rate=self.form.cleaned_data["rate"],
                created_by=self.request.user,
                modified_by=self.request.user,
            )
            route.save(run_on_reactor=False)  # save it but do not run reactor yet

            route.connectors.set(self.form.cleaned_data["connectors"])
            route.filters.set(self.form.cleaned_data["filters"])
            route.save()  # now run on reactor

            return route

    class List(BaseListView):
        title = "Routers"
        permission = "jasmin.jasminroute_list"
        paginator_class = Paginator
        paginate_by = 10


class JasminInterceptorCRUDL(SmartCRUDL):
    actions = ("create", "list", "update", "delete",)
    model = JasminInterceptor

    class Create(FormMixin, WorkspacePermsMixin, NonAtomicMixin, SmartCreateView):
        template_name = "jasmin/interceptor.html"
        title = "Create Interceptor"
        permission = "jasmin.jasmininterceptor_create"
        form_class = JasminInterceptorForm
        success_url = "@jasmin.jasmininterceptor_list"

        def get_form_kwargs(self):
            kwargs = super().get_form_kwargs()
            kwargs["workspace"] = self.derive_workspace()
            return kwargs

        def save(self, obj):
            interceptor = JasminInterceptor(
                interceptor_type=self.form.cleaned_data["interceptor_type"],
                nature=self.form.cleaned_data["nature"],
                workspace=self.derive_workspace(),
                order=self.form.cleaned_data["order"],
                script=self.form.cleaned_data["script"],
                created_by=self.request.user,
                modified_by=self.request.user,
            )
            interceptor.save(run_on_reactor=False)  # save it but do not run reactor yet

            interceptor.filters.set(self.form.cleaned_data["filters"])
            interceptor.save()  # now run on reactor

            return obj

    class List(BaseListView):
        title = "MT Interceptors"
        permission = "jasmin.jasmininterceptor_list"
        paginator_class = Paginator
        paginate_by = 10

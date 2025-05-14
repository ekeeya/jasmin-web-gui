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
from django.http import HttpResponseRedirect
from django.urls import reverse
from smartmin.mixins import NonAtomicMixin
from smartmin.views import SmartCRUDL, SmartCreateView, SmartListView, SmartUpdateView, SmartDeleteView

from quark.jasmin.models import JasminGroup, JasminUser, JasminSMPPConnector, JasminFilter, JasminRoute, \
    JasminInterceptor
from quark.jasmin.views.forms import JasminGroupForm, UpdateJasminGroupForm, JasminUserForm, JasminSPPConnectorForm, \
    JasminFilterForm, JasminRouteForm, JasminInterceptorForm
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
        template_name = None
        # template_name = "jasmin/group_create.html"
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
        title = "Delete Jasmin Group"
        permission = "jasmin.jasmingroup_delete"
        success_url = "@jasmin.jasmingroup_list"


class JasminUserCRUDL(SmartCRUDL):
    actions = ("create", "list", "update", "delete",)
    model = JasminUser

    class Create(FormMixin, WorkspacePermsMixin, NonAtomicMixin, SmartCreateView):
        permission = "jasmin.jasminuser_create"
        form_class = JasminUserForm
        template_name = "jasmin/user_create.html"

        def get_form_kwargs(self):
            kwargs = super().get_form_kwargs()
            kwargs["workspace"] = self.derive_workspace()
            return kwargs

    class Update(FormMixin, WorkspacePermsMixin, NonAtomicMixin, SmartUpdateView):
        permission = "jasmin.jasminuser_update"
        template_name = "jasmin/user_create.html"
        form_class = JasminUserForm

        def get_form_kwargs(self):
            kwargs = super().get_form_kwargs()
            kwargs["workspace"] = self.derive_workspace()
            return kwargs

    class List(WorkspacePermsMixin, NonAtomicMixin, SmartListView):
        permission = "jasmin.jasminuser_list"
        fields = ("username", "groups", 'enabled', 'mt_credential', 'smpps_credential')

        def derive_queryset(self, **kwargs):
            # only users whose group belongs to our workspace
            return super().derive_queryset(**kwargs).filter(group__workspace=self.request.workspace)

    class Delete(WorkspacePermsMixin, NonAtomicMixin, SmartDeleteView):
        permission = "jasmin.jasminuser_delete"
        redirect_url = "@jasmin.jasminuser_list"


class JasminSMPPConnectorCRUDL(SmartCRUDL):
    actions = ("configure", "list", "update", "delete",)
    model = JasminSMPPConnector

    class Configure(FormMixin, WorkspacePermsMixin, NonAtomicMixin, SmartCreateView):
        title = "Configure SMPP Connector"
        permission = "jasmin.jasminsmppconnector_configure"
        form_class = JasminSPPConnectorForm
        success_url = "@jasmin.jasminsmppconnector_list"

        def get_form_kwargs(self):
            kwargs = super().get_form_kwargs()
            kwargs["workspace"] = self.derive_workspace()
            return kwargs

    class List(BaseListView):
        title = "SMPP Connectors"
        permission = "jasmin.jasminsmppconnector_list"
        paginator_class = Paginator
        paginate_by = 10
        fields = ("id", "cid", "host", "port", "is_active")

        def get_context_data(self, **kwargs):
            context = super().get_context_data(**kwargs)
            workspace = self.derive_workspace()
            context['workspace'] = workspace

            return context


class JasminFilterCRUDL(SmartCRUDL):
    actions = ("create", "list", "update", "delete",)
    model = JasminFilter

    class Create(FormMixin, WorkspacePermsMixin, NonAtomicMixin, SmartCreateView):
        title = "Create Message Filter"
        permission = "jasmin.jasminfilter_create"
        form_class = JasminFilterForm
        success_url = "@jasmin.jasminfilter_list"

        def get_form_kwargs(self):
            kwargs = super().get_form_kwargs()
            kwargs["workspace"] = self.derive_workspace()
            return kwargs

    class List(BaseListView):
        title = "Message Filters"
        permission = "jasmin.jasminfilter_list"
        paginator_class = Paginator
        paginate_by = 10

        def get_context_data(self, **kwargs):
            context = super().get_context_data(**kwargs)
            workspace = self.derive_workspace()
            context['workspace'] = workspace

            return context


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

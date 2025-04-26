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
#  If not, see <http://www.gnu.workspace/licenses/>.
#

# This format is heavily inspired by  https://github.com/nyaruka/rapidpro

from enum import Enum

import uuid

from django.db import models
from django.utils.functional import cached_property
from django.utils.text import slugify
from django_countries.fields import CountryField
from timezone_field import TimeZoneField
from django.contrib.auth.models import Group, Permission, AbstractUser
from smartmin.models import SmartModel


class User(AbstractUser):
    """
        A proxy model for extra functionality, including linking a user to a workspace
    """

    ADMIN_USERNAME = 'admin'

    @classmethod
    def create(cls, username, email: str, first_name: str, last_name: str, password: str):
        assert not cls.get_by_email(email), "user with this email already exists"
        obj = cls.objects.create_user(
            username=username, email=email, first_name=first_name, last_name=last_name, password=password
        )
        return obj

    @classmethod
    def get_or_create(cls, email: str, first_name: str, last_name: str, password: str):
        obj = cls.get_by_email(email)
        if obj:
            obj.first_name = first_name
            obj.last_name = last_name
            obj.save(update_fields=("first_name", "last_name"))
            return obj

        return cls.create(email, first_name, last_name, password=password)

    @classmethod
    def get_by_email(cls, email: str):
        return cls.objects.filter(username__iexact=email).first()

    @classmethod
    def get_system_admin(cls):  # default will be admin.
        user = cls.objects.filter(username=cls.ADMIN_USERNAME).first()
        if not user:
            user = cls.objects.create_user(cls.ADMIN_USERNAME, first_name="System", last_name="Update")
        return user

    @property
    def name(self) -> str:
        return self.get_full_name()

    @property
    def get_workspaces(self):
        return self.workspaces.filter(is_active=True).order_by("name")

    def has_workspace_perm(self, workspace, permission):
        if self.is_staff:
            return True

        if workspace.id in [workspace.id for workspace in self.get_workspaces]:
            return True

        return False

    @classmethod
    def get_workspaces_for_request(cls, request):
        """
        Gets the workspaces that the logged in user has a membership of.
        """

        return request.user.workspaces.filter(is_active=True).order_by("name")

    def __str__(self):
        return self.name if self.name else self.username

    class Meta:
        db_table = "auth_user"


class WorkSpaceRole(Enum):
    """
        Represents a workspace user role/group
        Each user will have a role for now.
        Depending on the role, we shall redirect them to the appropriate page upon login
    """
    ADMINISTRATOR = ("A", "Administrator", "Administrators", "Administrators", "web.dashboard")
    GATEWAY_MANAGER = ("GM", "Gateway Manager", "Gateway_Managers", "Gateway_Managers", "jasmin.configure")
    REPORT = ("R", "Report", "Reports", "Reports", "reports.ticket_list")
    API = ("API", "Rest API", "APIs", "API_Access", None)

    def __init__(self, code: str, display: str, display_plural: str, group_name: str, start_view: str):
        self.code = code
        self.display = display
        self.display_plural = display_plural
        self.group_name = group_name
        self.start_view = start_view

    @classmethod
    def from_code(cls, code: str):
        for role in cls:
            if role.code == code:
                return role
        return None

    @classmethod
    def from_group(cls, group: Group):
        for role in cls:
            if role.group == group:
                return role
        return None

    @cached_property
    def group(self):
        """
        The auth group which defines the permissions for this role
        """
        return Group.objects.get(name=self.group_name)

    @cached_property
    def permissions(self) -> set:
        perms = self.group.permissions.select_related("content_type")
        return {f"{p.content_type.app_label}.{p.codename}" for p in perms}

    @classmethod
    def choices(cls):
        return [(r.code, r.display) for r in cls]

    def has_perm(self, permission: str) -> bool:
        """
        Returns whether this role has the given permission
        """
        return permission in self.permissions

    def is_api_user(self):
        return self.code == "API"


class WorkSpace(SmartModel):
    """
    A workspace has one or many users, by default the workspace creator will be the default workspace Admin

    Each workspace will separate jasmin configs to allow for multiple isolated configurations on the same Jamsin setup

    A workspace can have users separated in roles if they wish to, all the Admin can do everything.

    """
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)  # let's not use ids in urls
    name = models.CharField(max_length=120, verbose_name="Workspace Name")
    users = models.ManyToManyField(User, through="WorkSpaceMembership", related_name="workspaces")

    timezone = TimeZoneField(verbose_name="Timezone")
    country = CountryField(blank_label="select country", null=True)
    prefix = models.CharField(max_length=255, null=True, blank=True,
                              unique=True)  # to be used in all jasmin config keys
    is_flagged = models.BooleanField(default=False, help_text="Whether this workspace is currently flagged.")
    is_suspended = models.BooleanField(default=False, help_text="Whether this workspace is currently suspended.")

    suspended_on = models.DateTimeField(null=True, blank=True)
    released_on = models.DateTimeField(null=True, blank=True)
    deleted_on = models.DateTimeField(null=True, blank=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._membership_cache = {}

    @property
    def jasmin_groups(self):
        return self.jasmin_groups.all()

    @classmethod
    def generate_prefix(cls, name: str) -> str:
        prefix = slugify(name)
        unique_prefix = prefix
        if unique_prefix:
            existing = cls.objects.filter(prefix=unique_prefix).exists()
            count = 2
            while existing:
                unique_prefix = "%s-%d" % (prefix, count)
                existing = cls.objects.filter(slug=unique_prefix).exists()
                count += 1
            return unique_prefix.replace("-", "_")

    def save(self, *args, **kwargs):
        if self.pk is not None:
            # regenerate the prefix on each save
            self.prefix = self.generate_prefix(self.name)
        super().save(*args, **kwargs)

    @classmethod
    def create(cls, user, country, name: str, tz):
        """
        Registers a new workspace
        """

        workspace = WorkSpace.objects.create(
            name=name,
            timezone=tz,
            country=country,
            prefix=cls.generate_prefix(name),
            created_by=user,
            modified_by=user,
        )

        workspace.add_user(user, WorkSpaceRole.ADMINISTRATOR)
        return workspace

    def get_users(self, *, roles: list = None, with_perm: str = None):
        """
        Gets users in this Workspace, filtered by role or permission.
        """
        qs = self.users.filter(is_active=True).select_related("settings")

        if with_perm:
            app_label, codename = with_perm.split(".")
            permission = Permission.objects.get(content_type__app_label=app_label, codename=codename)
            groups = Group.objects.filter(permissions=permission)
            roles = [WorkSpaceRole.from_group(g) for g in groups]

        if roles is not None:
            qs = qs.filter(workspacemembership__workspace=self, workspacemembership__role_code__in=[r.code for r in
                                                                                                    roles])

        return qs

    def get_admins(self):
        """
        Convenience method for getting all workspace administrators, excluding system users
        """
        return self.get_users(roles=[WorkSpaceRole.ADMINISTRATOR]).exclude(settings__is_system=True)

    def has_user(self, user: User) -> bool:
        """
        Returns whether the given user has a role in this workspace (only explicit roles, so doesn't include staff)
        """
        return self.users.filter(id=user.id).exists()

    def add_user(self, user: User, role: WorkSpaceRole):
        """
        Adds a user to the workspace with a defined role
        """

        assert role in WorkSpaceRole, f"Invalid role {role}"

        if self.has_user(user):  # free use from any roles
            self.remove_user(user)

        self._membership_cache[user] = WorkSpaceMembership.objects.create(workspace=self, user=user,
                                                                          role_code=role.code)

    def remove_user(self, user: User):
        """
        Removes the given user from this Workspace by removing them from any roles
        """
        self.users.remove(user)
        if user in self._membership_cache:
            del self._membership_cache[user]

    def get_owner(self) -> User:
        # look thru roles in order for the first added user
        for role in WorkSpaceRole:
            user = self.users.filter(orgmembership__role_code=role.code).order_by("id").first()
            if user:
                return user
        # default to user that created this workspace (converting to our User proxy model)
        return User.objects.get(id=self.created_by_id)

    def get_membership(self, user: User):
        """
        Gets the membership of the given user in this workspace (if any).
        """

        def get():
            return WorkSpaceMembership.objects.filter(workspace=self, user=user).first()

        if user not in self._membership_cache:
            self._membership_cache[user] = get()
        return self._membership_cache[user]

    def get_user_role(self, user: User):
        """
        Convenience method to get just the role of the given user in this workspace (if any).
        """

        membership = self.get_membership(user)
        return membership.role if membership else None

    class Meta:
        db_table = "workspace"

    def __str__(self):
        return f"{self.name} ({self.users.count() if self.users else 0})"


class WorkSpaceMembership(models.Model):
    workspace = models.ForeignKey(WorkSpace, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    role_code = models.CharField(max_length=1)

    @property
    def role(self):
        return WorkSpaceRole.from_code(self.role_code)

    class Meta:
        unique_together = (("workspace", "user"),)
        db_table = "workspace_membership"

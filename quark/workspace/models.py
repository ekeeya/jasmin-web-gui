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

    JASMIN_LINK_UNSET = ""
    JASMIN_LINK_DEMO = "demo"
    JASMIN_LINK_CUSTOM = "custom"
    JASMIN_LINK_CHOICES = (
        (JASMIN_LINK_UNSET, "Not configured"),
        (JASMIN_LINK_DEMO, "Local demo Jasmin"),
        (JASMIN_LINK_CUSTOM, "My own Jasmin"),
    )

    jasmin_link = models.CharField(
        max_length=16,
        choices=JASMIN_LINK_CHOICES,
        default=JASMIN_LINK_UNSET,
        blank=True,
        help_text="How this workspace reaches Jasmin: demo gateway or your own.",
    )

    # Custom remote Jasmin (used when jasmin_link=custom). Passwords are Fernet-encrypted.
    jasmin_router_pb_host = models.CharField(max_length=255, blank=True, default="")
    jasmin_router_pb_port = models.PositiveIntegerField(null=True, blank=True)
    jasmin_router_pb_username = models.CharField(max_length=128, blank=True, default="")
    jasmin_router_pb_password = models.CharField(max_length=512, blank=True, default="")

    jasmin_smpp_pb_host = models.CharField(max_length=255, blank=True, default="")
    jasmin_smpp_pb_port = models.PositiveIntegerField(null=True, blank=True)
    jasmin_smpp_pb_username = models.CharField(max_length=128, blank=True, default="")
    jasmin_smpp_pb_password = models.CharField(max_length=512, blank=True, default="")

    jasmin_http_api_url = models.URLField(max_length=512, blank=True, default="")
    jasmin_rest_api_url = models.URLField(
        max_length=512,
        blank=True,
        default="",
        help_text=(
            "Optional Jasmin REST API base URL (sendbatch). Without REST, Jasmin uses the "
            "native HTTP API; leave empty to keep Joyce bulk on async HTTP /send."
        ),
    )
    jasmin_connection_tested_at = models.DateTimeField(null=True, blank=True)

    # External messaging channel (Joyce API + optional DLR forward)
    messaging_api_enabled = models.BooleanField(
        default=False,
        help_text="When enabled, external apps can POST SMS via Joyce's token-authenticated API.",
    )
    messaging_api_token = models.CharField(
        max_length=64,
        blank=True,
        default="",
        db_index=True,
        help_text="Bearer token for the Joyce messaging API. Regenerate from workspace settings.",
    )
    external_dlr_url = models.URLField(
        max_length=512,
        blank=True,
        default="",
        help_text="Optional external channel URL. Joyce forwards DLRs here after internal handling.",
    )
    external_dlr_method = models.CharField(
        max_length=8,
        choices=(("POST", "POST"), ("GET", "GET")),
        default="POST",
        help_text="HTTP method used when forwarding DLRs to the external channel.",
    )
    external_dlr_retry_delay_secs = models.PositiveIntegerField(
        default=60,
        help_text="Seconds between external DLR forward retries (default 60).",
    )
    external_dlr_max_retries = models.PositiveIntegerField(
        default=5,
        help_text="Max forward attempts to the external DLR URL (default 5).",
    )

    jasmin_user_sync_interval_mins = models.PositiveIntegerField(
        default=5,
        help_text=(
            "How often (minutes) to pull live Jasmin user credentials/quotas into Django. "
            "Set to 0 to disable automatic sync for this workspace."
        ),
    )
    jasmin_user_last_synced_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When Jasmin user credentials were last synced into Django for this workspace.",
    )
    jasmin_config_last_imported_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When full Jasmin config (groups/users/connectors/routes/…) was last pulled into Django.",
    )

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
            return unique_prefix.replace("-", "").replace("_", "")

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

    def jasmin_custom_fields_complete(self) -> bool:
        """True when all custom remote Jasmin connection fields are present."""
        return bool(
            self.jasmin_router_pb_host
            and self.jasmin_router_pb_port
            and self.jasmin_router_pb_username
            and self.jasmin_router_pb_password
            and self.jasmin_smpp_pb_host
            and self.jasmin_smpp_pb_port
            and self.jasmin_smpp_pb_username
            and self.jasmin_smpp_pb_password
            and self.jasmin_http_api_url
        )

    def clear_jasmin_custom_connection(self, *, save: bool = True):
        """Drop stored custom Jasmin endpoints/credentials (keeps sync interval)."""
        self.jasmin_router_pb_host = ""
        self.jasmin_router_pb_port = None
        self.jasmin_router_pb_username = ""
        self.jasmin_router_pb_password = ""
        self.jasmin_smpp_pb_host = ""
        self.jasmin_smpp_pb_port = None
        self.jasmin_smpp_pb_username = ""
        self.jasmin_smpp_pb_password = ""
        self.jasmin_http_api_url = ""
        self.jasmin_rest_api_url = ""
        self.jasmin_connection_tested_at = None
        if save:
            self.save(
                update_fields=[
                    "jasmin_router_pb_host",
                    "jasmin_router_pb_port",
                    "jasmin_router_pb_username",
                    "jasmin_router_pb_password",
                    "jasmin_smpp_pb_host",
                    "jasmin_smpp_pb_port",
                    "jasmin_smpp_pb_username",
                    "jasmin_smpp_pb_password",
                    "jasmin_http_api_url",
                    "jasmin_rest_api_url",
                    "jasmin_connection_tested_at",
                    "modified_on",
                ]
            )

    def is_jasmin_ready(self) -> bool:
        """
        Whether this workspace may use Configure/Operate against Jasmin.

        The workspace must opt into demo Jasmin or finish a custom connection.
        """
        if self.jasmin_link == self.JASMIN_LINK_DEMO:
            return True
        if self.jasmin_link == self.JASMIN_LINK_CUSTOM:
            return self.jasmin_custom_fields_complete()
        return False

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

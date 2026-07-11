from django.contrib.auth import get_user_model
from django.test import TestCase
from jasmin.routing.jasminApi import Group

from .models import JasminGroup
from .reactor import run_in_reactor
from .router_pb import RouterPBInterface

User = get_user_model()


class GroupTestCase(TestCase):
    """
    Integration tests, these require a reachable Jasmin RouterPB
    (see JASMIN_ROUTER_PB_* settings).
    """

    def setUp(self):
        self.router = RouterPBInterface()
        self.user, _ = User.objects.get_or_create(username="ekeeya", defaults={'password': '12345678'})

        self.group, created = JasminGroup.objects.get_or_create(
            gid='test',
            defaults=dict(
                created_by=self.user,
                modified_by=self.user,
                description="Unit tests"
            )
        )

    def test_group_creation(self):
        self.assertIsInstance(self.group, JasminGroup)

    def test_jasmin_group_creation(self):
        groups = run_in_reactor(self.router.get_all_groups)

        self.assertIsInstance(groups, list, "Result is not a list")
        self.assertTrue(all(isinstance(item, Group) for item in groups),
                        "Not all items are instances of Jasmin Group")

        group_jasmin = next((item for item in groups if item.gid == self.group.gid), None)
        self.assertIsInstance(group_jasmin, Group)

    def test_remove_group(self):
        result = run_in_reactor(self.router.remove_groups, self.group.gid)
        self.assertIsNotNone(result)

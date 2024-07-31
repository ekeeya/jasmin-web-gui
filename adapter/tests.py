from django.contrib.auth.models import User
from django.test import TestCase
from .models import JasminGroup
from .router_pb import RouterPBInterface
from quark.utils import logger
from jasmin.routing.jasminApi import Group


class GroupTestCase(TestCase):
    def setUp(self):
        self.router = RouterPBInterface()
        self.group_jasmin = None
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
        def handle_result(result):
            logger.debug(f"Result from Twisted operation: {result}")
            self.assertIsInstance(result, list, "Result is not a list")
            self.assertTrue(all(isinstance(item, Group) for item in result),
                            "Not all items are instances of Jasmin Group")

            for item in result:
                if item.gid == self.group.gid:
                    self.group_jasmin = item
                    break
            self.assertIsInstance(self.group_jasmin, Group)

        def handle_error(error):
            logger.error("Error in Twisted operation:")
            raise error

        deferred = self.router.get_all_groups()
        deferred.addCallbacks(handle_result, handle_error)
        self.router.set_deferred(deferred)
        self.router.execute()

    def test_remove_group(self):
        def handle_result(result):
            logger.debug(f"Group successfully removed: {result}")

        def handle_error(error):
            logger.error(f"Error in Twisted operation: {error}")
            raise error

        deferred = self.router.remove_groups(self.group.gid)
        deferred.addCallbacks(handle_result, handle_error)
        self.router.set_deferred(deferred)
        self.router.execute()

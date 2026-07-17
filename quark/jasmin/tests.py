from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import SimpleTestCase, TestCase
from jasmin.routing.Routes import DefaultRoute, StaticMORoute
from jasmin.routing.jasminApi import Group, HttpConnector

from .models import JasminGroup, JasminRoute
from .reactor import run_in_reactor
from .router_pb import RouterPBInterface

User = get_user_model()


class MORouteTestCase(SimpleTestCase):
    def test_default_route_ignores_rate(self):
        connector = HttpConnector(
            cid="http_test",
            baseurl="https://example.com/mo",
            method="POST",
        )

        for rate in (None, Decimal("1.25")):
            with self.subTest(rate=rate):
                model = JasminRoute(
                    nature="MO",
                    router_type="DefaultRoute",
                    rate=rate,
                )
                route = model._create_mo_route([], [connector])

                self.assertIsInstance(route, DefaultRoute)
                self.assertEqual(route.getRate(), 0.0)

    def test_mo_route_uses_http_connector_only(self):
        http = HttpConnector(
            cid="http_mo",
            baseurl="https://example.com/mo",
            method="POST",
        )
        route = JasminRoute(
            nature="MO",
            router_type="StaticMORoute",
            order=10,
        )._create_mo_route([], [http])
        self.assertIsInstance(route, StaticMORoute)
        self.assertEqual(route.getConnector()._type, "http")

    def test_mo_rejects_when_building_without_http_connectors(self):
        """to_jasmin_route requires at least one HTTP or SMPP (smpps) connector for MO."""
        from unittest.mock import MagicMock, patch

        route = JasminRoute(nature="MO", router_type="DefaultRoute", order=0)
        empty = MagicMock()
        empty.all.return_value = []
        with patch.object(JasminRoute, "filters", empty), patch.object(
            JasminRoute, "smpp_connectors", empty
        ), patch.object(JasminRoute, "http_connectors", empty):
            with self.assertRaises(ValidationError) as ctx:
                route.to_jasmin_route()
        self.assertIn("HTTP or SMPP", str(ctx.exception))


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

#  Copyright (c) 2025
#  File created on 2025/5/3
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
from enum import Enum

from django.db import models
from jasmin.routing.Routes import (
    DefaultRoute,
    StaticMTRoute,
    StaticMORoute,
    RandomRoundrobinMORoute,
    RandomRoundrobinMTRoute,
    FailoverMTRoute,
    FailoverMORoute,
)

MO = "MO"
MT = "MT"


class MTRouter(Enum):
    DefaultRoute = DefaultRoute, ("A route without a filter, this one can only set with the lowest order to be a "
                                  "default/fallback route")
    StaticMTRoute = StaticMTRoute, "A basic route with Filters and one Connector"
    RandomRoundrobinMTRoute = RandomRoundrobinMTRoute, ("A route with Filters and many Connectors, will return a "
                                                        "random Connector if its Filters are matching, can be used "
                                                        "as a load balancer route")
    FailoverMTRoute = FailoverMTRoute, ("A route with Filters and many Connectors, will return an available ("
                                        "connected) Connector if its Filters are matched")

    @classmethod
    def jasmin_router_class(cls, field):
        return cls[field].value[0]


class MORouter(Enum):
    DefaultRoute = DefaultRoute, ("A route without a filter, this one can only set with the lowest order to be a "
                                  "default/fallback route")
    StaticMORoute = StaticMORoute, "A basic route with Filters and one Connector"
    RandomRoundrobinMORoute = RandomRoundrobinMORoute, ("A route with Filters and many Connectors, will return a "
                                                        "random Connector if its Filters are matching, can be used "
                                                        "as a load balancer route")
    FailoverMORoute = FailoverMORoute, ("A route with Filters and many Connectors, will return an available ("
                                        "connected) Connector if its Filters are matched")

    @classmethod
    def jasmin_router_class(cls, field):
        return cls[field].value[0]


class MTRouterChoices(models.TextChoices):
    DefaultRoute = "DefaultRoute", "Default route"
    StaticMTRoute = "StaticMTRoute", "Static MTRoute"
    RandomRoundrobinMTRoute = "RandomRoundrobinMTRoute", "Random Roundrobin MTRoute"
    FailoverMTRoute = "FailoverMTRoute", "Failover MTRoute"


class MORouterChoices(models.TextChoices):
    DefaultRoute = "DefaultRoute", "Default route"
    StaticMORoute = "StaticMORoute", "Static MORoute"
    RandomRoundrobinMORoute = "RandomRoundrobinMORoute", "Random Roundrobin MORoute"
    FailoverMORoute = "FailoverMORoute", "Failover MORoute"


class JasminBaseRouter(models.Model):
    rate = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )

    nature = models.CharField(
        max_length=2,
        choices=[("MO", "MO"), ("MT", "MT")]
    )
    workspace = models.ForeignKey("workspace.WorkSpace", on_delete=models.CASCADE)

    order = models.IntegerField(unique=True)

    class Meta:
        abstract = True

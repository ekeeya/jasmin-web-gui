#  Copyright (c) 2025
#  File created on 2025/5/16
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
from django.db import models
from jasmin.routing.jasminApi import Connector, SmppClientConnector


class ConnectorType(models.TextChoices):
    SMPP = "SMPP", "SMPP"
    HTTP = "HTTP", "HTTP"


class BaseJasminConnector(models.Model):
    cid = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        db_index=True,
    )

    connector_type = models.CharField(
        max_length=4,
        choices=ConnectorType.choices,
        default=ConnectorType.HTTP
    )
    workspace = models.ForeignKey("workspace.WorkSpace", on_delete=models.CASCADE)

    def make_cid(self):
        if self.cid is None: # make it once
            if self.connector_type == ConnectorType.SMPP.name:
                self.cid = f"smppc_{self.workspace.id}_{str(self.id)}"
                self.save(run_on_reactor=False)  # persist the cid do not post on jasmin PB
            else:
                self.cid = f"http_{self.workspace.id}_{str(self.id)}"
                self.save()  # persist the cid
        return self.cid

    def to_connector(self) -> Connector:
        """
        Concrete children can implement this, but by default re return and SMPP client connector
        """
        return SmppClientConnector(self.cid)

    class Meta:
        abstract = True

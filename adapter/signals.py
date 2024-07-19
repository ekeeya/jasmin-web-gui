#
#  Copyright (c) 2024
#  File created on 2024/7/19
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

from django.dispatch import receiver
from django.db.models.signals import post_save, post_delete
from twisted.internet import defer
from .models import JasminGroup
from .router_pb import RouterPBInterface
from quark.utils import logger


@receiver(post_save, sender=JasminGroup)
def save_group_to_jasmin(sender, instance, created, **kwargs):
    if created:
        try:
            router_pb = RouterPBInterface()

            @defer.inlineCallbacks
            def workflow():
                logger.debug("Starting the workflow to create group in Jasmin.")
                yield router_pb.connect()
                yield router_pb.add_group(instance.gid, True)
                router_pb.close()  # always close the reactor

            router_pb.execute(workflow)
            logger.debug("Created group in Jasmin.")
        except Exception as e:
            # set flag to prevent recursion
            instance._delete_flag = True
            instance.delete()
            logger.error("Could not create group in Jasmin. due to: {}".format(e))


@receiver(post_delete, sender=JasminGroup)
def remove_group_from_jasmin(sender, instance, **kwargs):
    # Check if the delete flag is set
    if hasattr(instance, '_delete_flag'):
        return

    # delete the group from Jasmin using the perspective broker API
    try:
        router_pb = RouterPBInterface()

        @defer.inlineCallbacks
        def workflow():
            logger.debug("Starting to remove group from Jasmin.")
            yield router_pb.connect()
            yield router_pb.group_remove(instance.gid)
            router_pb.close()

        router_pb.execute(workflow)
        logger.debug("Removed group from Jasmin.")
    except Exception as e:
        logger.error("Could not remove group in Jasmin. due to: {}".format(e))

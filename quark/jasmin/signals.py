#  Copyright (c) 2024
#  File created on 2024/7/30
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

from django.db.models.signals import pre_delete
from django.dispatch import receiver
from twisted.internet import defer
from quark.jasmin.router_pb import RouterPBInterface

from quark.utils import logger
from .models import JasminGroup


@receiver(pre_delete, sender=JasminGroup)
def delete_repo(sender, instance, **kwargs):
    router = RouterPBInterface()
    d = router.remove_groups(instance.gid)

    def on_failure(error):
        logger.error(error)
        raise Exception(f"Could not delete the group {instance.gid} from Jasmin due to: {error}")

    def on_success(result):
        logger.debug(f"Successfully deleted the group {instance.gid} from Jasmin")

    def ensure_completion(result_or_failure):
        # If there's an error, Django will recognize the exception and stop the deletion
        if isinstance(result_or_failure, defer.Failure):
            raise DeletionFailedException(f"Failed to remove group {instance.gid}: {result_or_failure}")

    d.addCallback(on_success)
    d.addErrback(on_failure)
    d.addBoth(ensure_completion)
    router.set_deferred(d)
    router.execute()


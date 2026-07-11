#
#  Copyright (c) 2024
#  File created on 2024/7/17
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

from django.apps import AppConfig


class AdapterConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'quark.jasmin'

    def ready(self):
        # The Twisted PB adapters (see quark/jasmin/*_pb.py) rely on a running
        # reactor. ready() is invoked by every Django entry point (runserver,
        # gunicorn workers, celery, management commands), so starting it here
        # covers them all. ensure_reactor_running() is idempotent and
        # thread-safe, so there is no double-start race.
        # NOTE: if you run gunicorn with --preload, the reactor thread would be
        # started in the master and lost on fork; don't use --preload, or call
        # ensure_reactor_running() from a post_fork hook instead.
        from quark.jasmin.reactor import ensure_reactor_running

        ensure_reactor_running()

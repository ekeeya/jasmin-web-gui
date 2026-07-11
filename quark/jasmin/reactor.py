#  Copyright (c) 2025
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
"""
Single place that owns the Twisted reactor lifecycle and the bridge between
Django's synchronous request threads and the reactor thread.

The reactor runs in a daemon thread, started lazily (and idempotently) by
``ensure_reactor_running()``. This is called from ``quark.jasmin.apps`` on app
startup so it works under manage.py, gunicorn workers and celery alike.

``run_in_reactor()`` is the only supported way to invoke the Jasmin PB proxies
from Django code: it schedules the call inside the reactor thread, blocks the
calling thread until the resulting Deferred fires, and re-raises any failure
in the calling thread so callers get a truthful success/failure outcome.
"""
import atexit
import logging
import queue
import threading

from django.conf import settings
from twisted.internet import defer, reactor
from twisted.python import failure

logger = logging.getLogger(__name__)

_reactor_lock = threading.Lock()
_reactor_thread = None

DEFAULT_TIMEOUT = 30


class JasminPBTimeoutError(Exception):
    """Raised when a Jasmin PB operation does not complete within the timeout"""


def _stop_reactor():
    if reactor.running:
        reactor.callFromThread(reactor.stop)


def ensure_reactor_running():
    """
    Starts the Twisted reactor in a daemon thread. Safe to call multiple times
    and from multiple threads; only the first call actually starts it.
    """
    global _reactor_thread

    with _reactor_lock:
        if reactor.running or (_reactor_thread is not None and _reactor_thread.is_alive()):
            return

        _reactor_thread = threading.Thread(
            target=lambda: reactor.run(installSignalHandlers=False),
            daemon=True,
            name="twisted-reactor",
        )
        _reactor_thread.start()
        atexit.register(_stop_reactor)
        logger.info("Twisted reactor started in background thread")


def run_in_reactor(fn, *args, timeout=None, **kwargs):
    """
    Runs ``fn(*args, **kwargs)`` inside the reactor thread and blocks the
    calling thread until the returned Deferred (if any) fires.

    Returns the operation result, or raises:
      - whatever exception the operation failed with (re-raised in this thread)
      - JasminPBTimeoutError if nothing came back within ``timeout`` seconds
    """
    ensure_reactor_running()

    if timeout is None:
        timeout = getattr(settings, "JASMIN_PB_TIMEOUT", DEFAULT_TIMEOUT)

    result_queue = queue.Queue()

    def _run():
        d = defer.maybeDeferred(fn, *args, **kwargs)
        d.addBoth(result_queue.put)

    reactor.callFromThread(_run)

    try:
        result = result_queue.get(timeout=timeout)
    except queue.Empty:
        raise JasminPBTimeoutError(
            f"Jasmin did not respond within {timeout}s, is the Jasmin PB service reachable?"
        )

    if isinstance(result, failure.Failure):
        result.raiseException()

    return result

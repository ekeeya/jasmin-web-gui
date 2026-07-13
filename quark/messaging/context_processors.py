#
#  Copyright (c) 2026
#
from quark.messaging.views.views import (
    CONSOLE_MODE_SESSION_KEY,
    MODE_CONFIGURE,
    MODE_OPERATE,
)


def console_mode(request):
    """Expose Configure vs Operate console mode to all templates."""
    mode = MODE_CONFIGURE
    if hasattr(request, "session"):
        raw = request.session.get(CONSOLE_MODE_SESSION_KEY, MODE_CONFIGURE)
        if raw in (MODE_CONFIGURE, MODE_OPERATE):
            mode = raw
    return {
        "joyce_console_mode": mode,
        "joyce_mode_configure": mode == MODE_CONFIGURE,
        "joyce_mode_operate": mode == MODE_OPERATE,
    }

"""
Server startstop hooks

This module contains functions called by Evennia at various
points during its startup, reload and shutdown sequence. It
allows for customizing the server operation as desired.

This module must contain at least these global functions:

at_server_init()
at_server_start()
at_server_stop()
at_server_reload_start()
at_server_reload_stop()
at_server_cold_start()
at_server_cold_stop()

"""

_PLAYTIME_TRACKER = None


def web_admin_apps(self, request, app_label=None):
    """
    This is a monkey-patch for the Evennia admin site to allow access to all models.
    It is patched in during at_server_init() below.
    """
    from django.conf import settings
    from django.contrib import admin

    app_list = admin.AdminSite.get_app_list(self, request, app_label=app_label)
    app_mapping = {app["app_label"]: app for app in app_list}
    out = [
        app_mapping.pop(app_label)
        for app_label in settings.DJANGO_ADMIN_APP_ORDER
        if app_label in app_mapping
    ]
    for app in settings.DJANGO_ADMIN_APP_EXCLUDE:
        app_mapping.pop(app, None)
    out += app_mapping.values()
    return out


def at_server_init():
    """
    This is called first as the server is starting up, regardless of how.
    """
    # Monkey-patch the Rich error handling into the Evennia cmdhandler.
    from evennia.commands import cmdhandler
    from athanor.error import _msg_err

    cmdhandler._msg_err = _msg_err

    # Monkey-patch the Evennia admin site to allow access to all models.
    from evennia.web.utils.adminsite import EvenniaAdminSite

    EvenniaAdminSite.get_app_list = web_admin_apps


def at_server_start():
    """
    This is called every time the server starts up, regardless of
    how it was shut down.
    """
    # from athanor.mudrich import install_mudrich
    # install_mudrich()

    from evennia.utils import callables_from_module, class_from_module, logger, repeat
    from django.conf import settings
    import athanor
    from athanor.utils import register_access_functions, register_lock_functions

    try:
        for k, v in settings.ATHANOR_RENDERER_MODULES.items():
            for module in v:
                athanor.RENDERERS[k].update(callables_from_module(module))
    except Exception:
        logger.log_trace()

    try:
        register_access_functions(settings.ACCESS_FUNCTIONS_LIST)
    except Exception:
        logger.log_trace()

    try:
        register_lock_functions(settings.DEFAULT_LOCKS_LIST)
    except Exception:
        logger.log_trace()

    for content_type, handler_dict in settings.ATHANOR_HANDLERS.items():
        for handler, handler_path in handler_dict.items():
            try:
                athanor.HANDLERS[content_type][handler] = class_from_module(
                    handler_path
                )
            except Exception:
                logger.log_trace()

    for t in ("UNLOGGEDIN", "SESSION", "CHARACTER", "ACCOUNT"):
        cmdsets = f"CMDSETS_{t}_EXTRA"
        cmdsets_from = getattr(settings, cmdsets)
        cmdsets_to = getattr(athanor, cmdsets)

        try:
            for cmdset in cmdsets_from:
                cmdsets_to.append(class_from_module(cmdset))
        except Exception:
            logger.log_trace()
            continue

        modules = f"CMD_MODULES_{t}"
        modules_from = getattr(settings, modules)
        modules_to = getattr(athanor, modules)

        try:
            for module in modules_from:
                modules_to.extend(callables_from_module(module).values())
        except Exception:
            logger.log_trace()
            continue

    from evennia.server import signals

    from .signal_handlers import (
        login_success,
        login_fail,
        django_login_fail,
        django_login_success,
    )

    signals.SIGNAL_ACCOUNT_POST_LOGIN.connect(login_success)
    signals.SIGNAL_ACCOUNT_POST_LOGIN_FAIL.connect(login_fail)

    from django.contrib.auth.signals import (
        user_logged_in,
        user_logged_out,
        user_login_failed,
    )

    user_logged_in.connect(django_login_success)
    user_login_failed.connect(django_login_fail)

    global _PLAYTIME_TRACKER
    from .utils import increment_playtime

    _PLAYTIME_TRACKER = repeat(
        settings.PLAYTIME_INTERVAL,
        increment_playtime,
        persistent=False,
        idstring="playtime",
    )


def at_server_stop():
    """
    This is called just before the server is shut down, regardless
    of it is for a reload, reset or shutdown.
    """
    from evennia.utils import unrepeat

    global _PLAYTIME_TRACKER
    if _PLAYTIME_TRACKER:
        unrepeat(_PLAYTIME_TRACKER)
        _PLAYTIME_TRACKER = None


def at_server_reload_start():
    """
    This is called only when server starts back up after a reload.
    """
    pass


def at_server_reload_stop():
    """
    This is called only time the server stops before a reload.
    """
    pass


def at_server_cold_start():
    """
    This is called only when the server starts "cold", i.e. after a
    shutdown or a reset.
    """
    # Cleanup all AthanorPlayerCharacters that are online...
    # but can't be, because we crashed. This should put them all
    # into storage and update all time trackers.
    from athanor.playviews import DefaultPlayview

    for pv in DefaultPlayview.objects.all():
        pv.at_cold_start()


def at_server_cold_stop():
    """
    This is called only when the server goes down due to a shutdown or
    reset.
    """
    from athanor.playviews import DefaultPlayview

    for pv in DefaultPlayview.objects.all():
        pv.at_cold_stop()

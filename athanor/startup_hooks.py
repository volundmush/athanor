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

def web_admin_apps(self, request, app_label=None):
    from django.conf import settings
    from django.contrib import admin
    app_list = admin.AdminSite.get_app_list(self, request, app_label=app_label)
    app_mapping = {app["app_label"]: app for app in app_list}
    out = [app_mapping.pop(app_label) for app_label in settings.DJANGO_ADMIN_APP_ORDER if app_label in app_mapping]
    for app in settings.DJANGO_ADMIN_APP_EXCLUDE:
        app_mapping.pop(app, None)
    out += app_mapping.values()
    return out


def at_server_init():
    """
    This is called first as the server is starting up, regardless of how.
    """
    from evennia.commands import cmdhandler
    from athanor.error import _msg_err

    cmdhandler._msg_err = _msg_err
    from evennia.web.utils.adminsite import EvenniaAdminSite
    EvenniaAdminSite.get_app_list = web_admin_apps


def at_server_start():
    """
    This is called every time the server starts up, regardless of
    how it was shut down.
    """
    #from athanor.mudrich import install_mudrich
    #install_mudrich()

    from evennia.utils import callables_from_module, class_from_module
    from django.conf import settings
    import athanor

    for t in ("UNLOGGEDIN", "SESSION", "CHARACTER", "ACCOUNT"):
        cmdsets = f"CMDSETS_{t}_EXTRA"
        cmdsets_from = getattr(settings, cmdsets)
        cmdsets_to = getattr(athanor, cmdsets)

        for cmdset in cmdsets_from:
            cmdsets_to.append(class_from_module(cmdset))

        modules = f"CMD_MODULES_{t}"
        modules_from = getattr(settings, modules)
        modules_to = getattr(athanor, modules)

        for module in modules_from:
            modules_to.extend(callables_from_module(module).values())


def at_server_stop():
    """
    This is called just before the server is shut down, regardless
    of it is for a reload, reset or shutdown.
    """
    pass


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
    from athanor.typeclasses.characters import AthanorPlayerCharacter
    for obj in AthanorPlayerCharacter.objects.get_by_tag(key="puppeted", category="account"):
        obj.at_post_unpuppet(last_logout=obj.db.last_online, shutdown=True)


def at_server_cold_stop():
    """
    This is called only when the server goes down due to a shutdown or
    reset.
    """
    pass

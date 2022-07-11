"""
Server startstop hooks

This module contains functions called by Evennia at various
points during its startup, reload and shutdown sequence. It
allows for customizing the server operation as desired.

This module must contain at least these global functions:

at_server_start()
at_server_stop()
at_server_reload_start()
at_server_reload_stop()
at_server_cold_start()
at_server_cold_stop()

"""

_ran_start = False


def at_always_start():
    global _ran_start
    if _ran_start:
        return
    else:
        _ran_start = True

    from mudrich import install_mudrich
    install_mudrich()

    from evennia.utils.utils import callables_from_module, class_from_module
    from django.conf import settings
    from athanor import MODIFIERS_ID, MODIFIERS_NAMES, SYSTEMS

    for mod_path in settings.MODIFIER_PATHS:
        for k, v in callables_from_module(mod_path).items():
            MODIFIERS_NAMES[v.category][v.get_name()] = v
            MODIFIERS_ID[v.category][v.modifier_id] = v

    for sys_path in settings.SYSTEMS:
        sys_class = class_from_module(sys_path)
        sys_obj = sys_class()
        SYSTEMS[sys_obj.name] = sys_obj

    for k, v in SYSTEMS.items():
        v.at_init()


def at_server_start():
    """
    This is called every time the server starts up, regardless of
    how it was shut down.
    """
    at_always_start()

    from athanor import SYSTEMS
    from twisted.internet import task
    from twisted.internet.defer import Deferred

    for k, v in SYSTEMS.items():
        v.at_start()

    for k, v in SYSTEMS.items():
        if v.interval > 0:
            v.looper = task.LoopingCall(lambda: Deferred.fromCoroutine(v.update()))
            v.task = v.looper.start(v.interval)


def at_server_stop():
    """
    This is called just before the server is shut down, regardless
    of it is for a reload, reset or shutdown.
    """
    from athanor import SYSTEMS

    for k, v in SYSTEMS.items():
        if v.task:
            v.task.cancel()
        v.at_stop()


def at_server_reload_start():
    """
    This is called only when server starts back up after a reload.
    """
    at_always_start()

    from athanor import SYSTEMS

    for k, v in SYSTEMS.items():
        v.at_reload_start()


def at_server_reload_stop():
    """
    This is called only time the server stops before a reload.
    """
    from athanor import SYSTEMS

    for k, v in SYSTEMS.items():
        v.at_reload_stop()


def at_server_cold_start():
    """
    This is called only when the server starts "cold", i.e. after a
    shutdown or a reset.
    """
    at_always_start()

    from athanor import SYSTEMS

    for k, v in SYSTEMS.items():
        v.at_cold_start()


def at_server_cold_stop():
    """
    This is called only when the server goes down due to a shutdown or
    reset.
    """
    from athanor import SYSTEMS

    for k, v in SYSTEMS.items():
        v.at_cold_stop()

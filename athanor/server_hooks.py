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
from collections import defaultdict


def at_server_init():
    from mudrich import install_mudrich
    install_mudrich()

    from evennia.utils.utils import callables_from_module, class_from_module
    from django.conf import settings
    from athanor import MODIFIERS_ID, MODIFIERS_NAMES, SYSTEMS, DG_VARS, DG_FUNCTIONS, DG_INSTANCE_CLASSES
    from athanor import EQUIP_SLOTS

    for p in settings.EQUIP_CLASS_PATHS:
        slots = callables_from_module(p)
        for k, v in slots.items():
            if not v.key and v.category:
                continue
            EQUIP_SLOTS[v.category][v.key] = v

    for k, v in settings.DG_INSTANCE_CLASSES.items():
        DG_INSTANCE_CLASSES[k] = class_from_module(v)

    for p in settings.DG_VARS:
        DG_VARS.update({k.lower(): v for k, v in callables_from_module(p).items()})

    dg_temp = defaultdict(dict)
    for category, mod_paths in settings.DG_FUNCTIONS.items():
        for func_path in mod_paths:
            for k, v in callables_from_module(func_path).items():
                dg_temp[category][k.lower()] = v
    shared = dict(dg_temp["shared"])

    for k, v in dg_temp.items():
        if k == "shared":
            continue
        DG_FUNCTIONS[k] = dict(shared)
        DG_FUNCTIONS[k].update(v)

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

    if settings.START_FUNCTION:
        func = class_from_module(settings.START_FUNCTION)

def at_server_start():
    """
    This is called every time the server starts up, regardless of
    how it was shut down.
    """

    from athanor import SYSTEMS
    from twisted.internet import task
    from twisted.internet.defer import Deferred

    for k, v in SYSTEMS.items():
        v.at_start()

    for k, v in SYSTEMS.items():
        #continue
        if v.interval > 0:
            v.task = Deferred.fromCoroutine(v.run())


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

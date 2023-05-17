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


def at_server_init():
    """
    This is called first as the server is starting up, regardless of how.
    """
    from mudrich import install_mudrich
    install_mudrich()

    from athanor.search import get_objs_with_key_or_alias
    from evennia.objects.manager import ObjectDBManager
    ObjectDBManager.get_objs_with_key_or_alias = get_objs_with_key_or_alias

    from evennia.utils.utils import callables_from_module
    from django.conf import settings

    from athanor import TRAIT_CLASSES
    for mod_path in settings.TRAIT_CLASS_PATHS:
        for k, v in callables_from_module(mod_path).items():
            if not hasattr(v, "slot_type"):
                continue
            TRAIT_CLASSES[v.slot_type][v.get_name()] = v

    from athanor import STAT_CLASSES
    for mod_path in settings.STAT_CLASS_PATHS:
        for k, v in callables_from_module(mod_path).items():
            if not getattr(v, "category", None):
                continue
            STAT_CLASSES[v.category][v.key()] = v

    from athanor import EFFECT_COMPONENT_CLASSES, EFFECT_CLASSES
    for mod_path in settings.EFFECT_COMPONENT_CLASS_PATHS:
        for k, v in callables_from_module(mod_path).items():
            if not hasattr(v, "get_key"):
                continue
            EFFECT_COMPONENT_CLASSES[v.get_key()] = v

    for mod_path in settings.EFFECT_CLASS_PATHS:
        for k, v in callables_from_module(mod_path).items():
            if not hasattr(v, "get_class_name"):
                continue
            EFFECT_CLASSES[v.get_class_name()] = v


def start_looping():
    from twisted.internet.task import LoopingCall
    from evennia.utils import class_from_module
    from athanor import LOOPING_DEFERREDS
    from django.conf import settings

    for name, data in settings.LOOPING_CALLS.items():
        callback = class_from_module(data['callback'])
        interval = data.get("interval", 10)
        looping_call = LoopingCall(callback)
        LOOPING_DEFERREDS[name] = looping_call
        looping_call.start(interval)


def at_server_start():
    """
    This is called every time the server starts up, regardless of
    how it was shut down.
    """
    start_looping()


def stop_looping():
    from athanor import LOOPING_DEFERREDS
    for looping_call in LOOPING_DEFERREDS.values():
        looping_call.stop()
    LOOPING_DEFERREDS.clear()


def at_server_stop():
    """
    This is called just before the server is shut down, regardless
    of it is for a reload, reset or shutdown.
    """
    stop_looping()


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
    for obj in AthanorPlayerCharacter.objects.filter_family():
        if obj.db.is_online:
            obj.at_post_unpuppet(last_logout=obj.db.last_online, shutdown=True)


def at_server_cold_stop():
    """
    This is called only when the server goes down due to a shutdown or
    reset.
    """
    from athanor import CHARACTERS_ONLINE
    for obj in set(CHARACTERS_ONLINE):
        obj.at_post_unpuppet(shutdown=True)

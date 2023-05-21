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
    ObjectDBManager.old_get_objs_with_key_or_alias = ObjectDBManager.get_objs_with_key_or_alias
    ObjectDBManager.get_objs_with_key_or_alias = get_objs_with_key_or_alias

    from evennia.utils.utils import callables_from_module
    from django.conf import settings

    from athanor import ASPECT_SLOT_CLASSES, QUIRK_SLOT_CLASSES, EFFECT_COMPONENT_CLASSES
    from athanor import EFFECT_CLASSES, ASPECT_CLASSES, QUIRK_CLASSES, STAT_CLASSES

    def load_categorized(paths, target_dict, key_name, attr_name=None):
        for mod_path in paths:
            for k, v in callables_from_module(mod_path).items():
                if not (key := getattr(v, key_name, None)):
                    continue
                if callable(key):
                    key = key()
                if attr_name:
                    if not (category := getattr(v, attr_name, None)):
                        continue
                    if callable(category):
                        category = category()
                    target_dict[category][key] = v
                else:
                    target_dict[key] = v

    for c in ((settings.ASPECT_SLOT_CLASS_PATHS, ASPECT_SLOT_CLASSES),
              (settings.QUIRK_SLOT_CLASS_PATHS, QUIRK_SLOT_CLASSES),
              (settings.EFFECT_COMPONENT_CLASS_PATHS, EFFECT_COMPONENT_CLASSES),
              (settings.EFFECT_CLASS_PATHS, EFFECT_CLASSES)):
        load_categorized(c[0], c[1], "get_key")

    for c in ((settings.ASPECT_CLASS_PATHS, ASPECT_CLASSES),
              (settings.QUIRK_CLASS_PATHS, QUIRK_CLASSES)):
        load_categorized(c[0], c[1], "get_key", "slot_type")

    load_categorized(settings.STAT_CLASS_PATHS, STAT_CLASSES, "category")


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
    for obj in AthanorPlayerCharacter.objects.get_by_tag(key="puppeted", category="account"):
        if obj.db.is_online:
            obj.at_post_unpuppet(last_logout=obj.db.last_online, shutdown=True)


def at_server_cold_stop():
    """
    This is called only when the server goes down due to a shutdown or
    reset.
    """
    pass

import typing
import sys
from athanor.utils import partial_match
from athanor import QUIRK_CLASSES, QUIRK_SLOT_CLASSES
from collections import defaultdict


class Quirk:
    """
    A Quirk is meant to represent one of many possible perks, flaws, bonuses, achievements-with-bonuses, or similar
    addition that can be added on to a character which may have mechanical impacts.

    The main difference between a Quirk and an Aspect is that a character may only have one of each kind of Aspect
    (it's hard to be both a Human and a Dwarf at once), but may have multiple Quirks in the same category.

    For instance, you may have at least two bonuses: Quick Fingered and Silver Tongued.

    Quirks are loaded into a character's QuirkSlots, managed by the QuirkHandler.
    Each Quirk is identified by a unique combination of its (slot_type, key) pair. These are loaded in from
    settings so it's easy to define and add new Quirks as classes.

    The recommended use of Quirks is to implement some form of call hooks on them, and also to have them
    apply Effects when they're added/loaded/removed/etc.
    """
    # An actual quirk must replace this with a not-empty string!
    slot_type = ""

    # A tuple of strings containing attribute names relevant to saving this quirk's current state.
    persistent_attrs = ()

    __slots__ = ["slot"]

    def __init__(self, slot, **kwargs):
        self.slot = slot

    @property
    def handler(self):
        return self.slot.handler

    @property
    def owner(self):
        return self.handler.owner

    @classmethod
    def get_key(cls):
        """
        The stat's key is its save key, and is used to identify it in the database.

        It need not be its display name. It should be a short string that is unique to this stat.

        By default, that's the class name, but a class property is good for overriding.
        """
        return getattr(cls, "key", cls.__name__.lower())

    def on_remove(self):
        """
        This method is called when the quirk is removed from the handler. A buff expires, a status effect wears off,
        a transformation ends, etc.
        """
        pass

    def on_add(self):
        """
        This method is called when the quirk is added to the handler. A buff is applied, a status effect is applied,
        a transformation is entered, etc.

        It's useful for setting defaults, sending messages, etc.
        """
        pass

    def on_load(self):
        """
        This method is called when the quirk is loaded on a character init. Use this to set up defaults or
        apply non-persistent Effects that the character should "always" have. This will probably look like a 'quieter'
        version of on_add.
        """
        pass

    @classmethod
    def get_name(cls):
        return getattr(cls, "name", cls.__name__)

    def __str__(self):
        return self.__class__.get_name()

    def __repr__(self):
        return f"<{self.slot_type} Quirk: {self.__class__.__name__}>"

    def export(self) -> dict:
        out = {attr: getattr(self, attr) for attr in self.persistent_attrs}
        out["key"] = self.get_key()
        return out

    def save(self):
        self.slot.save()

    def load_final(self):
        pass


class QuirkSlot:

    __slots__ = ["handler", "quirks"]

    @classmethod
    def get_key(cls):
        return getattr(cls, "key", cls.__name__).lower()

    def __init__(self, handler, **kwargs):
        self.handler = handler
        self.quirks = dict()

    @property
    def owner(self):
        return self.handler.owner

    def add_quirk(self, quirk, load=False, **kwargs):
        if quirk in self.quirks:
            return False, f"Quirk already present: {quirk}"
        if not (quirk_class := QUIRK_CLASSES[self.get_key()].get(quirk, None)):
            return False, f"Invalid quirk: {quirk}"
        new_quirk = quirk_class(self, **kwargs)
        self.quirks[quirk] = new_quirk
        if load:
            new_quirk.on_load()
        else:
            new_quirk.on_add()
            self.save()

    def remove_quirk(self, quirk: str):
        if (found := self.quirks.pop(quirk, None)):
            found.on_remove()
            self.save()
            return True, f"Quirk removed: {quirk}"
        return False, f"Quirk not found: {quirk}"

    def load(self, **data):
        for k, v in data.items():
            self.add_quirk(k, load=True, **v)

    def load_final(self):
        for quirk in self.quirks.values():
            quirk.load_final()

    def save(self):
        if self.quirks:
            data = {k: v.export() for k, v in self.quirks.items()}
            self.owner.attributes.add(category=self.handler.attr_category, key=self.get_key(), value=data)
        else:
            self.owner.attributes.remove(category=self.handler.attr_category, key=self.get_key())


class QuirkHandler:
    attr_category = "quirks"

    __slots__ = ["owner", "slots"]

    def __init__(self, owner):
        self.owner = owner
        self.slots = dict()
        self.load()

    def load(self):
        self.init_slots()
        if (save_data := self.owner.attributes.get(category=self.attr_category, return_list=True, return_obj=True)):
            save_data = [s for s in save_data if s]
            for attr in save_data:
                print(f"{attr.key}: {attr.value}")
                if attr.key in self.slots:
                    self.slots[attr.key].load(**attr.value)
        for slot in self.slots.values():
            slot.load_final()

    def init_slots(self):
        for k, v in self.owner.all_quirk_slots().items():
            if not (found_class := QUIRK_SLOT_CLASSES.get(k.lower(), None)):
                raise ValueError(f"Invalid quirk slot: {k}")
            self.slots[k] = found_class(self, **v)

    def add_quirk(self, slot: str, quirk: str, **kwargs) -> typing.Tuple[bool, str]:
        if not (found := self.slots.get(slot.lower(), None)):
            return False, f"Invalid slot: {slot}"
        return found.add_quirk(quirk.lower(), **kwargs)

    def remove_quirk(self, slot: str, quirk: str):
        if not (found := self.slots.get(slot, None)):
            return False, f"Invalid slot: {slot}"
        return found.remove_quirk(quirk)

    def get_quirk(self, slot: str) -> typing.Optional[Quirk]:
        if not (found := self.slots.get(slot, None)):
            return None
        return found.quirk

    def get_quirks(self):
        for slot in self.slots.values():
            for q in slot.quirks.values():
                yield q

    def active_slots(self):
        return [slot for slot in self.slots.values() if slot.quirk]

    def inactive_slots(self):
        return [slot for slot in self.slots.values() if not slot.quirk]

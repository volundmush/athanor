import typing
import sys
from athanor.utils import partial_match
from athanor import ASPECT_CLASSES, ASPECT_SLOT_CLASSES
from collections import defaultdict


class Aspect:
    """
    An Aspect is meant to represent a trait or property of a character for which they can have only one per a type.
    For instance, a character might be a Human, or a Dwarf, but not both at once.

    Aspects are loaded into a character's AspectSlots, managed by the AspectHandler.

    Each Aspect is identified by a unique combination of its (slot_type, key) pair. These are loaded in from
    settings so it's easy to define and add new Aspects as classes.

    The recommended use of Aspects is to implement some form of call hooks on them, and also to have them
    apply Effects when they're added/loaded/removed/etc.
    """
    # An actual aspect must replace this with a not-empty string!
    slot_type = ""

    # A tuple of strings containing attribute names relevant to saving this aspect's current state.
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
        return getattr(cls, "key", cls.__name__).lower()

    def on_remove(self):
        """
        This method is called when the aspect is removed from the handler. A buff expires, a status effect wears off,
        a transformation ends, etc.
        """
        pass

    def on_add(self):
        """
        This method is called when the aspect is added to the handler. A buff is applied, a status effect is applied,
        a transformation is entered, etc.

        It's useful for setting defaults, sending messages, etc.
        """
        pass

    def on_load(self):
        """
        This method is called when the aspect is loaded on a character init. Use this to set up defaults or
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
        return f"<{self.slot_type} Aspect: {self.__class__.__name__}>"

    def export(self) -> dict:
        out = {attr: getattr(self, attr) for attr in self.persistent_attrs}
        out["key"] = self.get_key()
        return out

    def save(self):
        self.slot.save()

    def load_final(self):
        pass


class AspectSlot:

    __slots__ = ["handler", "aspect"]

    @classmethod
    def get_key(cls):
        return getattr(cls, "key", cls.__name__).lower()

    def __init__(self, handler, **kwargs):
        self.handler = handler
        self.aspect = None

    @property
    def owner(self):
        return self.handler.owner

    def set_aspect(self, aspect, load=False, **kwargs):
        if self.aspect:
            self.remove_aspect()
        if not (aspect_class := ASPECT_CLASSES[self.get_key()].get(aspect.lower(), None)):
            return False, f"Invalid aspect: {aspect}"
        self.aspect = aspect_class(self, **kwargs)
        if load:
            self.aspect.on_load()
        else:
            self.aspect.on_add()
            self.aspect.save()

    def remove_aspect(self):
        if self.aspect:
            self.aspect.on_remove()
            self.owner.attributes.remove(category=self.handler.attr_category, key=self.get_key())
            self.aspect = None
            return True, "Aspect removed."
        return False, "No aspect to remove."

    def load(self, **data):
        if (key := data.pop("key", None)):
            self.set_aspect(key, load=True, **data)

    def load_final(self):
        if self.aspect:
            self.aspect.load_final()

    def save(self):
        if self.aspect:
            self.owner.attributes.add(category=self.handler.attr_category, key=self.get_key(), value=self.aspect.export())
        else:
            self.owner.attributes.remove(category=self.handler.attr_category, key=self.get_key())


class AspectHandler:
    attr_category = "aspects"

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
                if attr.key in self.slots:
                    self.slots[attr.key].load(**attr.value)
        for slot in self.slots.values():
            slot.load_final()

    def init_slots(self):
        for k, v in self.owner.all_aspect_slots().items():
            if not (found_class := ASPECT_SLOT_CLASSES.get(k.lower(), None)):
                raise ValueError(f"Invalid aspect slot: {k}")
            self.slots[k] = found_class(self, **v)

    def set_aspect(self, slot: str, aspect: str, **kwargs) -> typing.Tuple[bool, str]:
        if not (found := self.slots.get(slot.lower(), None)):
            return False, f"Invalid slot: {slot}"
        return found.set_aspect(aspect.lower(), **kwargs)

    def remove_aspect(self, slot: str):
        if not (found := self.slots.get(slot, None)):
            return False, f"Invalid slot: {slot}"
        if not found.aspect:
            return False, f"No aspect in slot: {slot}"
        return found.remove_aspect()

    def get_aspect(self, slot: str) -> typing.Optional[Aspect]:
        if not (found := self.slots.get(slot, None)):
            return None
        return found.aspect

    def get_aspects(self):
        return [slot.aspect for slot in self.slots.values() if slot.aspect]

    def active_slots(self):
        return [slot for slot in self.slots.values() if slot.aspect]

    def inactive_slots(self, slot_type=None):
        return [slot for slot in self.slots.values() if not slot.aspect]
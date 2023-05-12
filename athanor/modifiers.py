import typing
import sys
from athanor.utils import partial_match
from athanor import MODIFIERS_ID, MODIFIERS_NAMES
from collections import defaultdict

class Modifier:
    """
    A Modifier is meant to represent some kind of trait, perk, character class, race, long-lasting transformation, or
    similar that can be applied to a character. Along with Items, these are the second major source of Effects. Most
    Modifiers will probably simply apply and remove Effects when they're added/loaded/removed/etc, but they could be
    subclassed to do far more than just that if desired.

    Modifier Classes are loaded when Athanor starts, from a list of provided modules. This list is defined in
    settings.py and can be easily extended.

    Modifiers, like Items, are attached via a character's ModifierSlots, similar to EquipSlots. Slots have a 'key' which
    must be unique for that character, and slot_type, which determines the kind of Modifiers that it can store.

    For example, a Character might have two slots: "race_1" and "race_2", which are both of slot_type "race". This
    could allow for hybrid races or other special cases. A character might also have a slot "class" which is of type
    "class", and thus they can only have one character class. However, since it's possible to store data about Modifiers,
    one could easily create a Job Switch-style system ala Final Fantasy Tactics which allows for classes to have levels
    and be changed at will.
    """
    # All modifiers have an ID attached to their class.
    modifier_id = -1
    # An actual modifier must replace this with a not-empty string!
    slot_type = ""

    # A tuple of strings containing attribute names relevant to saving this modifier's current state.
    # It's not necessary to store 'modifier_id', 'category', or slot.
    persistent_attrs = ()

    def __init__(self, slot, **kwargs):
        """

        """
        self.slot = slot
        self.handler = slot.handler
        self.owner = self.handler.owner

    def on_remove(self, **kwargs):
        """
        This method is called when the modifier is removed from the handler. A buff expires, a status effect wears off,
        a transformation ends, etc.
        """
        pass

    def on_add(self, **kwargs):
        """
        This method is called when the modifier is added to the handler. A buff is applied, a status effect is applied,
        a transformation is entered, etc.

        It's useful for setting defaults, sending messages, etc.
        """
        pass

    def on_load(self, **kwargs):
        """
        This method is called when the modifier is loaded on a character init. Use this to set up defaults or
        apply non-persistent Effects that the character should "always" have. This will probably look like a 'quieter'
        version of on_add.
        """
        pass

    @classmethod
    def get_name(cls):
        return getattr(cls, "name", cls.__name__)

    def __str__(self):
        return self.__class__.get_name()

    def __int__(self):
        return self.modifier_id

    def __repr__(self):
        return f"<{self.__class__.__name__}: {int(self)}>"

    def export(self) -> dict:
        out = {"modifier_id": self.modifier_id}
        for attr in self.persistent_attrs:
            out[attr] = getattr(self, attr)
        return out


class ModifierSlot:

    def __init__(self, handler, key: str, slot_type: str, modifier=None, **kwargs):
        self.handler = handler
        self.owner = handler.owner
        self.key = sys.intern(key)
        self.slot_type = sys.intern(slot_type)
        self.modifier = modifier

    def set_modifier(self, modifier, load=False, **kwargs):
        if self.modifier:
            self.remove_modifier()
        self.modifier = modifier
        if load:
            self.modifier.on_load(**kwargs)
        else:
            self.modifier.on_add(**kwargs)
            self.modifier.save()

    def remove_modifier(self, **kwargs):
        if self.modifier:
            self.modifier.on_remove(**kwargs)
            self.owner.attributes.remove(category=self.handler.attr_category, key=self.key)
            self.modifier = None

    def save(self):
        if self.modifier:
            self.owner.attributes.add(category=self.handler.attr_category, key=self.key, value=self.modifier.export())


class ModifierHandler:
    attr_category = "modifiers"
    slot_class = ModifierSlot

    def __init__(self, owner):
        self.owner = owner
        self.slots = dict()
        self.slots_index = defaultdict(set)
        self.load()

    def load(self):
        self.init_slots()
        self.load_from_attribute()

    def init_slots(self):
        for k, v in self.owner.all_modifier_slots():
            mod_slot = self.slot_class(self, k, **v)
            self.slots_index[mod_slot.slot_type].add(mod_slot)
            self.slots[k] = mod_slot

    def load_from_attribute(self):
        to_clean = set()
        for attr in self.owner.attributes.get(category=self.attr_category):
            if not (slot := self.slots.get(attr.key, None)):
                to_clean.add(attr.key)
                continue
            if "modifier_id" not in attr.value:
                to_clean.add(attr.key)
                continue
            if not (modifier_class := self._get_modifier_class(slot.slot_type, attr.value["modifier_id"])):
                to_clean.add(attr.key)
                continue
            slot.set_modifier(modifier_class(slot, **attr.value))

        for key in to_clean:
            self.owner.attributes.remove(category=self.attr_category, key=key)

    def save(self, slot: str = None):
        if slot and (found := self.slots.get(slot, None)):
            found.save()
        else:
            for slot in self.slots.values():
                slot.save()

    def _get_modifier_class(self, slot_type: str, mod) -> typing.Optional[typing.Type[Modifier]]:
        if slot_type not in MODIFIERS_NAMES:
            return None
        if hasattr(mod, "modifier_id"):
            return mod
        found = None
        if isinstance(mod, int):
            found = MODIFIERS_ID[slot_type].get(mod, None)
        elif isinstance(mod, str):
            fname = partial_match(mod, MODIFIERS_NAMES[slot_type].keys())
            found = MODIFIERS_NAMES[slot_type].get(fname, None)
        return found if found else None

    def add_modifier(self, slot: str, modifier: typing.Union[int, str], **kwargs) -> typing.Tuple[bool, str]:
        if not (found := self.slots.get(slot, None)):
            return False, f"Invalid slot: {slot}"
        if not (modifier_class := self._get_modifier_class(found.slot_type, modifier)):
            return False, f"Invalid modifier: {modifier}"
        try:
            modif = modifier_class(found, **kwargs)
            found.set_modifier(modif, **kwargs)
        except Exception as e:
            return False, f"Error adding modifier: {e}"
        return True, ""

    def remove_modifier(self, slot: str):
        if not (found := self.slots.get(slot, None)):
            return False, f"Invalid slot: {slot}"
        if not found.modifier:
            return False, f"No modifier in slot: {slot}"
        found.remove_modifier()
        return True, ""

    def get_modifiers(self, slot_type=None):
        return [slot.modifier for slot in
                (self.slots.values() if slot_type is None else self.slots_index.get(slot_type, set()))
                if slot.modifier]

    def active_slots(self, slot_type=None):
        if slot_type:
            return {key: slot for key, slot in self.slots.items() if slot.modifier and slot.slot_type == slot_type}
        return {key: slot for key, slot in self.slots.items() if slot.modifier}

    def inactive_slots(self, slot_type=None):
        if slot_type:
            return {key: slot for key, slot in self.slots.items() if not slot.modifier and slot.slot_type == slot_type}
        return {key: slot for key, slot in self.slots.items() if not slot.modifier}
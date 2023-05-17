import typing
import sys
from athanor.utils import partial_match
from athanor import TRAIT_CLASSES
from collections import defaultdict


class Trait:
    """
    A Trait is meant to represent some kind of trait, perk, character class, race, long-lasting transformation, or
    similar that can be applied to a character. Along with Items, these are the second major source of Effects. Most
    Traits will probably simply apply and remove Effects when they're added/loaded/removed/etc, but they could be
    subclassed to do far more than just that if desired.

    Trait Classes are loaded when Athanor starts, from a list of provided modules. This list is defined in
    settings.py and can be easily extended.

    Traits, like Items, are attached via a character's TraitSlots, similar to EquipSlots. Slots have a 'key' which
    must be unique for that character, and slot_type, which determines the kind of Traits that it can store.

    For example, a Character might have two slots: "race_1" and "race_2", which are both of slot_type "race". This
    could allow for hybrid races or other special cases. A character might also have a slot "class" which is of type
    "class", and thus they can only have one character class. However, since it's possible to store data about Traits,
    one could easily create a Job Switch-style system ala Final Fantasy Tactics which allows for classes to have levels
    and be changed at will.
    """
    # An actual trait must replace this with a not-empty string!
    slot_type = ""

    # A tuple of strings containing attribute names relevant to saving this trait's current state.
    persistent_attrs = ()

    def __init__(self, slot, **kwargs):
        """

        """
        self.slot = slot
        self.handler = slot.handler
        self.owner = self.handler.owner

    @classmethod
    def key(cls):
        """
        The stat's key is its save key, and is used to identify it in the database.

        It need not be its display name. It should be a short string that is unique to this stat.

        By default, that's the class name, but a class property is good for overriding.
        """
        return getattr(cls, "key", cls.__name__)

    def on_remove(self, **kwargs):
        """
        This method is called when the trait is removed from the handler. A buff expires, a status effect wears off,
        a transformation ends, etc.
        """
        pass

    def on_add(self, **kwargs):
        """
        This method is called when the trait is added to the handler. A buff is applied, a status effect is applied,
        a transformation is entered, etc.

        It's useful for setting defaults, sending messages, etc.
        """
        pass

    def on_load(self, **kwargs):
        """
        This method is called when the trait is loaded on a character init. Use this to set up defaults or
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
        return f"<{self.slot_type} Trait: {self.__class__.__name__}>"

    def export(self) -> dict:
        out = {attr: getattr(self, attr) for attr in self.persistent_attrs}
        out["key"] = self.key()
        return out


class TraitSlot:

    def __init__(self, handler, key: str, slot_type: str, trait=None, **kwargs):
        self.handler = handler
        self.owner = handler.owner
        self.key = sys.intern(key)
        self.slot_type = sys.intern(slot_type)
        self.trait = trait

    def set_trait(self, trait, load=False, **kwargs):
        if self.trait:
            self.remove_trait()
        self.trait = trait
        if load:
            self.trait.on_load(**kwargs)
        else:
            self.trait.on_add(**kwargs)
            self.trait.save()

    def remove_trait(self, **kwargs):
        if self.trait:
            self.trait.on_remove(**kwargs)
            self.owner.attributes.remove(category=self.handler.attr_category, key=self.key)
            self.trait = None

    def save(self):
        if self.trait:
            self.owner.attributes.add(category=self.handler.attr_category, key=self.key, value=self.trait.export())


class TraitHandler:
    attr_category = "traits"
    slot_class = TraitSlot

    def __init__(self, owner):
        self.owner = owner
        self.slots = dict()
        self.slots_index = defaultdict(set)
        self.load()

    def load(self):
        self.init_slots()
        self.load_from_attribute()

    def init_slots(self):
        for k, v in self.owner.all_trait_slots():
            mod_slot = self.slot_class(self, k, **v)
            self.slots_index[mod_slot.slot_type].add(mod_slot)
            self.slots[k] = mod_slot

    def load_from_attribute(self):
        to_clean = set()
        for attr in self.owner.attributes.get(category=self.attr_category):
            if not (slot := self.slots.get(attr.key, None)):
                to_clean.add(attr.key)
                continue
            if "key" not in attr.value:
                to_clean.add(attr.key)
                continue
            if not (trait_class := self._get_trait_class(slot.slot_type, attr.value["key"])):
                to_clean.add(attr.key)
                continue
            slot.set_trait(trait_class(slot, **attr.value))

        for key in to_clean:
            self.owner.attributes.remove(category=self.attr_category, key=key)

    def save(self, slot: str = None):
        if slot and (found := self.slots.get(slot, None)):
            found.save()
        else:
            for slot in self.slots.values():
                slot.save()

    def _get_trait_class(self, slot_type: str, key: str) -> typing.Optional[typing.Type[Trait]]:
        if slot_type not in TRAIT_CLASSES:
            return None
        return TRAIT_CLASSES[slot_type].get(key, None)

    def add_trait(self, slot: str, trait: str, **kwargs) -> typing.Tuple[bool, str]:
        if not (found := self.slots.get(slot, None)):
            return False, f"Invalid slot: {slot}"
        if not (trait_class := self._get_trait_class(found.slot_type, trait)):
            return False, f"Invalid trait: {trait}"
        try:
            trait = trait_class(found, **kwargs)
            found.set_trait(trait, **kwargs)
        except Exception as e:
            return False, f"Error adding trait: {e}"
        return True, ""

    def remove_trait(self, slot: str):
        if not (found := self.slots.get(slot, None)):
            return False, f"Invalid slot: {slot}"
        if not found.trait:
            return False, f"No trait in slot: {slot}"
        found.remove_trait()
        return True, ""

    def get_traits(self, slot_type=None):
        return [slot.trait for slot in
                (self.slots.values() if slot_type is None else self.slots_index.get(slot_type, set()))
                if slot.trait]

    def active_slots(self, slot_type=None):
        if slot_type:
            return {key: slot for key, slot in self.slots.items() if slot.trait and slot.slot_type == slot_type}
        return {key: slot for key, slot in self.slots.items() if slot.trait}

    def inactive_slots(self, slot_type=None):
        if slot_type:
            return {key: slot for key, slot in self.slots.items() if not slot.trait and slot.slot_type == slot_type}
        return {key: slot for key, slot in self.slots.items() if not slot.trait}
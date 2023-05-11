import sys
import typing


class EquipSlot:
    """
    A base equipment slot class that's used for representing where and how an item might be equipped.
    Presumably, that means equipped to a character, but the system isn't limited like that. You might
    equip engines to a spaceship, or a saddle to a horse. The EquipHandler is responsible for managing
    the EquipSlots and the EquipSlots are responsible for managing and describing
    the actual items that are equipped.
    """

    # The attributes which should be saved to the attribute-dict for this equip slot, if it's persistent.
    # There's no need for this to contain 'key', 'persistent' or 'item'.
    persistent_attrs = ["slot_type", "sort_order", "wear_verb", "wear_display", "remove_verb", "remove_display"]

    def __init__(self, handler, key: str, slot_type: str, list_display: str, sort_order: int = 0,
                 wear_verb: str = "$conj(wears)", wear_display: str = "on $pron(your) body",
                 remove_verb: str = "$conj(removes)", remove_display: str = "from $pron(your) body",
                 persistent: bool = False, item=None):

        # The EquipHandler managing this EquipSlot.
        self.handler = handler

        # The object that owns this EquipSlot - and whatever it has equipped.
        self.owner = handler.owner

        # a short string like "right_ring_finger" which uniquely describes this equip slot for this character.
        # It is used for an Attribute key so make sure it really is unique for this character.
        self.key = sys.intern(key)

        # The actual Object being stored in this slot. It could be None if the slot is empty.
        self.item = item
        if self.item:
            self.item.attributes.add(key=self.handler.item_attr, value=self.key)

        # A short string like "finger", "neck", or "hand" which describes the type of slot this is.
        # A character might have multiple slots of the same type, but only one of each key.
        # For instance, key="right_ring_finger" and key="left_ring_finger" would both have slot_type "finger".
        # An Item should have an equip_type that matches the slot_type of the slot it's being equipped to.
        # Items could be equippable in multiple slot_types, but they can only be equipped to one slot at a time.
        self.slot_type = sys.intern(slot_type)

        # A number that determines the order in which this slot is displayed in a list of slots.
        self.sort_order = sort_order

        # A string that describes how the character wears this item. For instance, "$conj(wears)".
        self.wear_verb = sys.intern(wear_verb)

        # A string that describes how the character wears this item. For instance, "on $pron(your) body".
        self.wear_display = sys.intern(wear_display)

        # A string that describes how the character removes this item. For instance, "$conj(removes)".
        self.remove_verb = sys.intern(remove_verb)

        # A string that describes how the character removes this item. For instance, "from $pron(your) body".
        self.remove_display = sys.intern(remove_display)

        # How this slot is displayed in a list of slots. For instance, "On Right Ring Finger".
        self.list_display = sys.intern(list_display) if list_display else None

        # Whether or not this slot is persistent. This is for optimization purposes. Many slots are
        # generated/provided by race/body type and are always available. In such case, there is no need
        # to save ALL of this EquipSlot's details to Attributes, just the key and item.
        # Other slots might be added via special traits or bonuses and be standalone, and will remain even
        # if a character's race somehow changes, as an example. Those special ones should be persistent.
        self.persistent = persistent

    def display_slot(self):
        if self.list_display:
            return self.list_display
        return self.__class__.__name__

    def display_contents(self, looker, **kwargs):
        """
        A method for displaying what's in this slot.
        """
        return self.item.get_display_name(looker=looker, **kwargs)

    def is_available(self):
        """
        For certain reasons, a character might have an equip slot, but it may not be available. For instance,
        a shield slot might be available only if the character is wielding a one-handed weapon. Alternatively,
        a right ring finger might only be available if the character has a right arm (without a missing hand).
        """
        return True

    def can_equip(self, item) -> typing.Tuple[bool, str]:
        """
        Determines whether or not the item can be equipped to this slot.
        """
        # Under no circumstances can a non-item be equipped!
        if "item" not in item._content_types:
            return False, f"{item.get_display_name(looker=self.owner)} is not an item!"
        if self.slot_type in item.get_equip_types():
            return True, ""

    def save(self):
        """
        Saves this EquipSlot to the owner's Attributes.
        """
        out = dict()
        if self.item:
            out["item"] = self.item
        if self.persistent:
            out["persistent"] = True
            for attr in self.persistent_attrs:
                out[attr] = getattr(self, attr)
        self.owner.attributes.add(category=self.handler.attr_category, key=self.key, value=out)


class EquipHandler:
    attr_category = "equip_slots"
    item_attr = "equip_slot"
    equip_class = EquipSlot

    def __init__(self, owner):
        self.owner = owner
        self.slots: typing.Dict[str, EquipSlot] = dict()
        self.load()

    def load(self):
        """
        Loads the EquipSlots from the owner's Attributes.
        """
        slot_data = self.owner.all_equip_slots()

        for key, data in self.owner.attributes.get(category=self.attr_category).items():
            value = data.value
            if key in slot_data:
                # this should NOT be a persistent slot. So we only need to retrieve 'item' from the data.
                slot_data[key].item = value.get("item", None)
            else:
                slot_data[key] = value

        self.slots = {self.equip_class(handler=self, key=key, **value) for key, value in slot_data.items()}
        self.sort()

        self.clean_attribute()

    def sort(self):
        """
        Sorts the slots by sort_order.
        """
        sorted_d = {k: self.slots[k] for k in sorted(self.slots, key=lambda x: self.slots[x]["sort_order"])}
        self.slots = sorted_d

    def save(self):
        """
        Saves the EquipSlots to the owner's Attributes.
        """
        for slot in self.slots.values():
            slot.save()

    def add_slot(self, key: str, **kwargs) -> typing.Tuple[bool, str]:
        """
        Adds a new EquipSlot to the handler.

        Args:
            key (str): The key for the slot. It must be unique for this character.

        Kwargs:
            The kwargs should contain the fields of the equip_class constructor, like slot_type
            and sort_order and wear_verb and so on.
        """
        if not kwargs:
            return False, "You must provide some kwargs!"
        if key in self.slots:
            return False, f"{key} already exists!"
        try:
            kwargs["persistent"] = True
            if "item" in kwargs:
                del kwargs["item"]
            slot = self.equip_class(handler=self, key=key, **kwargs)
            self.slots[key] = slot
            slot.save()
        except Exception as e:
            return False, str(e)
        self.sort()
        return True, ""

    def remove_slot(self, key: str) -> typing.Tuple[bool, str]:
        """
        Removes an EquipSlot from the handler.

        Args:
            key (str): The key for the slot.
        """
        if not (slot := self.slots.get(key, None)):
            return False, f"{key} does not exist!"
        if not slot.persistent:
            return False, f"{key} is not persistent!"
        if slot.item:
            return False, f"{key} has an item equipped!"
        del self.slots[key]
        self.clean_attribute()
        return True, ""

    def clean_attribute(self):
        """
        Checks to see if there are non-persistent slots in the attribute category which don't correspond to
        loaded slots and removes the unneeded data.
        """
        for key, data in self.owner.attributes.get(category=self.attr_category).items():
            if key not in self.slots and not data.value.get("persistent", False):
                self.owner.attributes.remove(category=self.attr_category, key=key)

    def occupied(self):
        """
        Returns a dictionary containing only the slots which have items equipped.
        """
        return {k: v for k, v in self.slots.items() if v.item}

    def empty(self):
        """
        Returns a dictionary containing only the slots which do not have items equipped.
        """
        return {k: v for k, v in self.slots.items() if not v.item}
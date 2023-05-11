import typing
from collections import defaultdict
from athanor.utils import partial_match
from athanor.exceptions import DatabaseError
from athanor import MODIFIERS_ID, MODIFIERS_NAMES


class Modifier:
    """
    A Modifier is meant to represent some kind of trait, perk, buff, status effect, or other thing that can be applied
    to a character which would have an effect on them. This might be a stat boost, a damage over time effect, or
    something else entirely. The modifier is meant to be subclassed and have its methods overridden to provide the
    desired behavior.

    Modifiers are loaded when Athanor starts, from a list of provided modules. This list is defined in settings.py and
    can be easily extended.

    Modifiers are attached to a handler, which is a class that is meant to handle the application of modifiers to the
    character. Examples are provided below as ModifierHandler and ModifiersHandler.

    If a Modifier instance attached to a character should keep track of persistent state, it's recommended to use the
    categorized DB Attributes on the owner.

    For example, self.owner.attributes.get(category=f"modifiers:{self.category}:{self.modifier_id}, key="field") as the
    default scheme.

    Note that the default implementation will remove these attributes when the Modifier is removed from the handler. If
    the modifier should be responsive to other data persistently (such as in the case of a transformation that gets
    better the longer you use it, but you can turn it on and off), you might want to use other Attributes for
    storing such.

    In the case of stacking, like multiple applications of Poison, it is recommended to have a single instance of the
    Poison modifier, but to use an attribute to store how many times it's been applied, by who, and at what intensity,
    how long until it wears off, and other details.
    """
    # All modifiers have an ID attached to their class.
    modifier_id = -1
    # An actual modifier must replace this with a not-empty string!
    category = ""
    # A tuple of unique strings which will be used to index this modifier on the Handler. This describes the 'type'
    # of modifier this is. For example, a buff might have the tags ('buff', 'stat', 'strength') That would allow you
    # to retrieve 'all modifiers that are buffs', 'all modifiers that affect strength', or 'all modifiers that affect
    # stats', as an example.
    mod_tags: typing.Tuple[str] = tuple()

    def __init__(self, owner, handler):
        """
        Args:
            owner (AthanorObject): The object that this modifier is attached to.
            handler: The handler that this modifier is attached to.
        """
        self.owner = owner
        self.handler = handler

    def attr_category(self) -> str:
        """
        Returns the category that this modifier should use for its persistent attributes.
        """
        return f"modifiers:{self.category}:{self.modifier_id}"

    def set_value(self, key: str, value):
        self.owner.attributes.add(category=self.attr_category(), key=key, value=value)

    def get_value(self, key: str, default=None):
        return self.owner.attributes.get(category=self.attr_category(), key=key,
                                         default=default)

    def on_remove(self, **kwargs):
        """
        This method is called when the modifier is removed from the handler. A buff expires, a status effect wears off,
        a transformation ends, etc.
        """
        self.owner.attributes.remove(category=f"modifiers:{self.category}:{self.modifier_id}")

    def on_add(self, **kwargs):
        """
        This method is called when the modifier is added to the handler. A buff is applied, a status effect is applied,
        a transformation is entered, etc.

        It's useful for setting defaults, sending messages, etc.
        """

    @classmethod
    def get_name(cls):
        if hasattr(cls, "name"):
            return cls.name
        return cls.__name__

    def __str__(self):
        if hasattr(self.__class__, "name"):
            return self.name
        return self.__class__.__name__

    def __int__(self):
        return self.modifier_id

    def __repr__(self):
        return f"<{self.__class__.__name__}: {int(self)}>"


class _ModHandlerBase:

    def __init__(self, owner, attr_name: str, mod_category: str):
        self.owner = owner
        self.attr_name = attr_name
        self.mod_category = mod_category
        self.mod_index = defaultdict(set)

    def _get_modifier(self, mod) -> typing.Optional[Modifier]:
        if hasattr(mod, "modifier_id"):
            return mod(self.owner, self)
        found = None
        if isinstance(mod, int):
            found = MODIFIERS_ID[self.mod_category].get(mod, None)
        elif isinstance(mod, str):
            fname = partial_match(mod, MODIFIERS_NAMES[self.mod_category].keys())
            found = MODIFIERS_NAMES[self.mod_category].get(fname, None)
        return found(self.owner, self) if found else None

    def add_modifier(self, modifier: Modifier):
        for stat in modifier.mod_tags:
            self.mod_index[stat].add(modifier)

    def remove_modifier(self, modifier: Modifier):
        for stat in modifier.mod_tags:
            self.mod_index[stat].remove(modifier)
            if not self.mod_index[stat]:
                del self.mod_index[stat]

    def get_modifiers(self, stat_name: str):
        return self.mod_index.get(stat_name, list())


class ModifierHandler(_ModHandlerBase):
    """
    Class used as a base for handling single Modifier types, like Race, Character Class, ItemType, Room Sector, etc.

    This can be used as-is, but may need to be extended considerably depending on how elaborate your modifiers are.
    """

    def __init__(self, owner, attr_name, mod_category: str, default=0):
        """
        Set up the ModifiersHandler.

        Args:
            owner (ObjectDB): The game object that'll have the modifier.
            attr_name: The attribute that'll be used to store the modifier ID.
            mod_category: The category index for MODIFIERS_NAMES[idx] and MODIFIERS_ID[idx]
        """
        super().__init__(owner, attr_name, mod_category)
        self.modifier = None
        self.default = default
        self.load()

    def load(self):
        data = self.owner.attributes.get(self.attr_name, default=self.default)
        if found := self._get_modifier(data):
            self.modifier = found

    def get(self) -> typing.Optional[Modifier]:
        return self.modifier

    def all(self):
        return [self.modifier] if self.modifier else []

    def set(self, modifier: typing.Union[int, str, typing.Type[Modifier]], strict: bool = False):
        """
        Used to set a modifier to owner. It will replace existing one.

        Args:
            modifier (int or str): ID or name (case insensitive) of modifier.
                Or the class instance.
            strict (bool): raise error if modifier doesn't exist.

        Raises:
            DatabaseError if modifier does not exist.
        """
        if found := self._get_modifier(modifier):
            if self.modifier:
                self.modifier.on_remove()
                self.remove_modifier(self.modifier)
                self.modifier = None
            self.modifier = found
            found.on_add()
            self.save()
            self.add_modifier(found)
            return self.modifier
        if strict:
            raise DatabaseError(f"{self.mod_category} {modifier} not found!")

    def save(self):
        if self.modifier:
            self.owner.attributes.add(key=self.attr_name, value=self.modifier.modifier_id)
        else:
            self.owner.attributes.remove(key=self.attr_name)

    def clear(self):
        if self.modifier:
            self.modifier.on_remove()
            self.remove_modifier(self.modifier)
        self.modifier = None
        self.save()


class ModifiersHandler(_ModHandlerBase):
    """
    Class used as a base for handling multiple Modifier types, like Status Effects, Buffs, Perks, Flaws, etc.

    It is meant to be instantiated via @lazy_property on an ObjectDB typeclass.
    """

    def __init__(self, owner, attr_name: str, mod_category: str):
        """
        Set up the ModifiersHandler.

        Args:
            owner (ObjectDB): The game object that'll have the modifiers.
            attr_name: The attribute that'll be used to store the modifier IDs.
            mod_category: The category index for MODIFIERS_NAMES[idx] and MODIFIERS_ID[idx]
        """
        super().__init__(owner, attr_name, mod_category)
        self.modifiers_names = dict()
        self.modifiers_ids = dict()
        self.default = list()
        self.load()

    def load(self):
        """
        Called by init. Retrieves IDs from attribute and references against the loaded
        modifiers.
        """
        data = self.owner.attributes.get(key=self.attr_name, default=self.default)
        for f in data:
            if found := self._get_modifier(f):
                self.modifier_ids[found.modifier_id] = found
                self.modifiers_names[str(found)] = found
                self.add_modifier(found)

    def save(self):
        """
        Serializes and sorts the Modifier IDs and saves to Attribute.
        """
        self.owner.attributes.add(self.attr_name, sorted(self.modifiers_ids.keys()))

    def has(self, modifier: typing.Union[int, str, typing.Type[Modifier]]) -> bool:
        """
        Called to determine if owner has this modifier.

        Args:
            modifier (int or str): ID or name (case insensitive) of modifier.

        Returns:
            answer (bool): Whether owner has modifier.
        """
        if hasattr(modifier, "modifier_id"):
            return modifier.modifier_id in self.modifiers_ids
        if isinstance(modifier, int) and modifier in self.modifiers_ids:
            return True
        if isinstance(modifier, str) and partial_match(modifier, self.modifiers_names.keys(), exact=True):
            return True
        return False

    def all(self, mod_tag: typing.Optional[str] = None) -> typing.Iterable[Modifier]:
        """
        Get all Modifiers of this type on owner.
        Largely useful for iteration.

        Returns:
            List of modifiers.
        """
        if mod_tag:
            return self.get_modifiers(mod_tag)
        return list(self.modifiers_ids.values())

    def add(self, modifier: typing.Union[int, str, typing.Type[Modifier]], strict=False):
        """
        Used to add a modifier to owner.

        Args:
            modifier (int or str): ID or name (case insensitive) of modifier.
            strict (bool): raise error if modifier doesn't exist.

        Raises:
            DatabaseError if modifier does not exist.
        """
        if found := self._get_modifier(modifier):
            self.modifiers_ids[found.modifier_id] = found
            self.modifiers_names[str(found)] = found
            self.add_modifier(found)
            found.on_add()
            self.save()
            return found
        if strict:
            raise DatabaseError(f"{self.mod_category} {modifier} not found!")

    def find(self, modifier, strict=False):
        """
        Used to add a modifier to owner.

        Args:
            modifier (int or str): ID or name (case insensitive) of modifier.
            strict (bool): raise error if modifier doesn't exist.

        Raises:
            DatabaseError if modifier does not exist.
        """
        if isinstance(modifier, int):
            if (found := self.modifiers_ids.get(modifier, None)):
                return found
        if isinstance(modifier, str):
            if (found := partial_match(modifier, self.modifiers_names.values(), exact=True)):
                return found
        if strict:
            raise DatabaseError(f"{self.mod_category} {modifier} not found!")

    def remove(self, modifier: typing.Union[int, str], strict=False):
        """
        Removes a modifier if owner has it.

        Args:
            modifier (int or str): ID or name (case insensitive) of modifier.
            strict (bool): raise error if modifier doesn't exist.

        Raises:
            DatabaseError if modifier does not exist.
        """
        if found := self.find(modifier, strict=strict):
            self.remove_modifier(found)
            found.on_remove()
            self.modifiers_ids.pop(found.modifier_id, None)
            self.modifiers_names.pop(str(found), None)
            self.save()
            return
        if strict:
            raise DatabaseError(f"{self.mod_category} {modifier} not found!")
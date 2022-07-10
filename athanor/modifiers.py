
class Modifier:
    modifier_id = -1

    def __init__(self, owner):
        self.owner = owner

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

    def stat_multiplier(self, obj, stat_name) -> float:
        return 0.0

    def stat_bonus(self, obj, stat_name) -> int:
        return 0


class FlagHandler:
    """
    Class used as a base for handling single Modifier types, like Race, Sensei, ItemType, RoomSector.
    """

    def __init__(self, owner, attr_name, mod_category: str, default=0):
        """
        Set up the FlagsHandler.

        Args:
            owner (ObjectDB): The game object that'll have the flag.
            attr_name: The attribute that'll be used to store the flag ID.
            mod_category: The category index for MODIFIERS_NAMES[idx] and MODIFIERS_ID[idx]
        """
        self.owner = owner
        self.attr_name = attr_name
        self.mod_category = mod_category
        self.modifier = None
        self.default = default
        self.load()

    def load(self):
        data = self.owner.attributes.get(self.attr_name, default=self.default)
        if (found := MODIFIERS_ID[self.mod_category].get(data, None)):
            self.modifier = found(self.owner)

    def get(self) -> typing.Optional["Modifier"]:
        return self.modifier

    def all(self):
        if self.modifier:
            return [self.modifier]
        return []

    def set(self, flag: typing.Union[int, str, typing.Type["Modifier"]], strict: bool = False):
        """
        Used to set a flag to owner. It will replace existing one.

        Args:
            flag (int or str): ID or name (case insensitive) of flag.
            strict (bool): raise error if flag doesn't exist.

        Raises:
            DatabaseError if flag does not exist.
        """
        if hasattr(flag, "mod_id"):
            self.modifier = flag(self.owner)
            self.save()
            return self.modifier

        if isinstance(flag, int):
            if (found := MODIFIERS_ID[self.mod_category].get(flag, None)):
                self.modifier = found(self.owner)
                self.save()
                return self.modifier
        if isinstance(flag, str):
            if (fname := partial_match(flag, MODIFIERS_NAMES[self.mod_category].keys())):
                found = MODIFIERS_NAMES[self.mod_category][fname]
                self.modifier = found(self.owner)
                self.save()
                return self.modifier
        if strict:
            raise DatabaseError(f"{self.mod_category} {flag} not found!")

    def save(self):
        if self.modifier:
            self.owner.attributes.add(self.attr_name, self.modifier.modifier_id)
        else:
            self.owner.attributes.remove(self.attr_name)

    def clear(self):
        self.modifier = None
        self.save()


class FlagsHandler:
    """
    Class used as a base for handling PlayerFlags, RoomFlags, MobFlags, and similar.

    It is meant to be instantiated via @lazy_property on an ObjectDB typeclass.

    These are objects loaded into advent.MODIFIERS_NAMES and MODIFIERS_ID.
    """

    def __init__(self, owner, attr_name: str, mod_category: str):
        """
        Set up the FlagsHandler.

        Args:
            owner (ObjectDB): The game object that'll have the flags.
            attr_name: The attribute that'll be used to store the flag IDs.
            mod_category: The category index for MODIFIERS_NAMES[idx] and MODIFIERS_ID[idx]
        """
        self.owner = owner
        self.attr_name = attr_name
        self.mod_category = mod_category
        self.modifiers_names = dict()
        self.modifiers_ids = dict()
        self.load()

    def load(self):
        """
        Called by init. Retrieves IDs from attribute and references against the loaded
        modifiers.
        """
        data = self.owner.attributes.get(self.attr_name, default=list())
        found = [fo for f in data if (fo := MODIFIERS_ID[self.mod_category].get(f, None))]
        for f in found:
            m = f(self.owner)
            self.modifiers_ids[m.modifier_id] = m
            self.modifiers_names[str(m)] = m

    def save(self):
        """
        Serializes and sorts the Modifier IDs and saves to Attribute.
        """
        self.owner.attributes.add(self.attr_name, sorted(self.modifiers_ids.keys()))

    def has(self, flag: typing.Union[int, str, typing.Type["Modifier"]]) -> bool:
        """
        Called to determine if owner has this flag.

        Args:
            flag (int or str): ID or name (case insensitive) of flag.

        Returns:
            answer (bool): Whether owner has flag.
        """
        if hasattr(flag, "mod_id"):
            flag = flag.mod_id
        if isinstance(flag, int) and flag in self.modifiers_ids:
            return True
        if isinstance(flag, str) and partial_match(flag, self.modifiers_names.keys(), exact=True):
            return True
        return False

    def all(self) -> typing.Iterable["Modifier"]:
        """
        Get all Flags of this type on owner.
        Largely useful for iteration.

        Returns:
            List of modifiers.
        """
        return list(self.modifiers_ids.values())

    def add(self, flag: typing.Union[int, str, typing.Type["Modifier"]], strict=False):
        """
        Used to add a flag to owner.

        Args:
            flag (int or str): ID or name (case insensitive) of flag.
            strict (bool): raise error if flag doesn't exist.

        Raises:
            DatabaseError if flag does not exist.
        """
        if hasattr(flag, "mod_id"):
            m = flag(self.owner)
            self.modifiers_ids[m.modifier_id] = m
            self.modifiers_names[str(m)] = m
            self.save()
            return

        if isinstance(flag, int):
            if (found := MODIFIERS_ID[self.mod_category].get(flag, None)):
                m = found(self.owner)
                self.modifiers_ids[m.modifier_id] = m
                self.modifiers_names[str(m)] = m
                self.save()
                return
        if isinstance(flag, str):
            if (fname := partial_match(flag, MODIFIERS_NAMES[self.mod_category].keys())):
                found = MODIFIERS_NAMES[self.mod_category][fname]
                m = found(self.owner)
                self.modifiers_ids[m.modifier_id] = m
                self.modifiers_names[str(m)] = m
                self.save()
                return
        if strict:
            raise DatabaseError(f"{self.mod_category} {flag} not found!")

    def remove(self, flag: typing.Union[int, str], strict=False):
        """
        Removes a flag if owner has it.

        Args:
            flag (int or str): ID or name (case insensitive) of flag.
            strict (bool): raise error if flag doesn't exist.

        Raises:
            DatabaseError if flag does not exist.
        """
        if isinstance(flag, int):
            if (found := self.modifiers_ids.pop(flag, None)):
                self.modifiers_names.pop(str(found))
                self.save()
                return
        if isinstance(flag, str):
            if (found := partial_match(flag, self.modifiers_ids.values(), exact=True)):
                self.modifiers_ids.pop(found.mod_id, None)
                self.modifiers_names.pop(str(found), None)
                self.save()
                return
        if strict:
            raise DatabaseError(f"{self.mod_category} {flag} not found!")
import typing
from athanor import STAT_CLASSES


class Stat:
    """
    A Stat is a base value and a formula used to calculate a derived value for that stat from modifiers
    and other values. For instance, a character's effective carry capacity might be a stat derived from
    Strength and Level.

    Given how easily customizable stats are, it's recommended that you subclass this class and override
    methods and add more to it fit for your game.
    """
    category = None

    __slots__ = ("handler", "value", "cache")

    def __init__(self, handler):
        self.handler = handler
        self.value = 0.0
        self.cache = None

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

    def default(self) -> float:
        return 0.0

    def __str__(self):
        return self.get_key()

    def base_value(self) -> float:
        return self.value

    def set(self, value: float):
        """
        Set the stat's flat value to the given value.
        """
        self.value = value
        self.save()

    def modify(self, value: float):
        """
        Modify the stat's flat value by the given value.
        """
        self.set(self.value + value)

    def get(self) -> float:
        """
        Return the stat's flat value.
        """
        return self.value

    def save(self):
        """
        Save the stat to the database.
        """
        self.owner.attributes.add(category=self.handler.save_category(), key=self.get_key(), value=self.value)

    def load(self):
        """
        Load the stat from the database.
        """
        self.value = self.owner.attributes.get(category=self.handler.save_category(), key=self.get_key(),
                                               default=self.default())

    def get_dynamic(self) -> float:
        """
        This should calculate the stat's value based on its base value and any modifiers.
        """
        return self.base_value()

    def calculate(self) -> float:
        """
        This should calculate the current/effective value of the stat after all modifiers and other factors
        are applied. If this needs the results of another stat, use self.handler.get_effective(stat_key, clear=False).

        BE CAREFUL TO AVOID INFINITE LOOPS. Stats should not be dependent on each other in a way that leads to
        one.
        """
        return self.value

    def effective(self) -> float:
        """
        This should calculate the current/effective value of the stat after all modifiers and other factors
        are applied.
        """
        if self.cache is None:
            self.cache = self.calculate()
        return self.cache

    def calculate_modifier(self, modifier: str) -> float:
        """
        Helper method which calculates the value of a modifier, calling all dynamics.
        """
        if not (modifier := self.owner.effects.modifiers.get(modifier, None)):
            return 0.0
        total = modifier.value
        for dynamic in modifier.dynamics:
            total += dynamic.on_calculate()
        return total


class StatHandler:
    """
    The StatHandler exists on AthanorMixin.stats and is used to manage an object's stats.

    The Handler can be created with a stat_category, which is a string that will be used
    to identify the group of Stats assigned to this object. Example stat_categories:
    "character", "item", "room", "spaceship".
    """

    __slots__ = ("owner", "stats", "stat_categories")

    def __init__(self, owner, stat_categories: typing.Iterable[str]):
        self.owner = owner
        self.stat_categories = stat_categories
        self.stats = dict()
        self.load()

    def load(self):
        for category in self.stat_categories:
            for stat in STAT_CLASSES.get(category, list()):
                self.stats[stat.get_key()] = stat(self)
        for k, v in self.stats.items():
            v.load()

    def save_category(self):
        return f"stats"

    def get_base(self, stat: str) -> float:
        """
        This is the access method for getting base stats. Use this because it can cache complex
        derived stat lookups and save on processing time.
        """
        if not (stat := self.stats.get(stat.lower(), None)):
            return 0.0
        return stat.base_value()

    def get_effective(self, stat: str, clear=True) -> float:
        """
        This is the access method for getting current stats. Use this because it can cache complex
        derived stat lookups and save on processing time.

        use clear=False if you want to get multiple stats in a row without clearing the cache.
        This is best used by the calculate() method of a stat, so it can benefit from the cache.
        """
        if not (stat := self.stats.get(stat.lower(), None)):
            return 0.0
        out_value = stat.effective()
        if clear:
            for stat in self.stats.values():
                stat.cache = None
        return out_value

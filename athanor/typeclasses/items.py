from .mixin import AthanorBase
from evennia.objects.objects import DefaultObject


class AthanorItem(DefaultObject, AthanorBase):
    _content_types = ("item",)

    def is_equipped(self) -> bool:
        return bool(self.db.equip_slot)

    def on_equip(self):
        """
        A hook that's called when the object is unequipped.

        Without exception, the character equipping the object must be self.location.

        This hook is likely going to be used to apply Effects to the character.
        """

    def on_unequip(self):
        """
        A hook that's called when the object is unequipped.

        Again, the character equipping the object must be self.location.

        This hook will likely be used to remove Effects from the character.
        """
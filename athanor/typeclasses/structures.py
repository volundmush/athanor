import typing
from evennia import DefaultObject
from .mixin import AthanorBase


class AthanorStructure(DefaultObject, AthanorBase):
    _content_types = ("structure",)

    def at_pre_move(self, destination: typing.Optional[DefaultObject], **kwargs):
        """
        Called just before moving object to destination.
        If returns False, move is cancelled.
        """
        if not destination:
            return True

        # Characters may only exist inside Rooms, Sectors, or Grids.
        return any(ctype in destination._content_types for ctype in ("room", "grid", "sector"))
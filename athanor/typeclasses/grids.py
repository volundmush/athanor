import typing
from evennia import DefaultObject
from .mixin import AthanorBase


class AthanorGrid(DefaultObject, AthanorBase):
    _content_types = ("grid",)

    def at_pre_move(self, destination: typing.Optional[DefaultObject], **kwargs):
        """
        Called just before moving object to destination.
        If returns False, move is cancelled.
        """
        # Grids can't be anywhere.
        if not destination:
            return True

    def at_object_receive(self, obj: DefaultObject, source_location: typing.Optional[DefaultObject], move_type="move", **kwargs):
        """
        Called after an object has been moved into this object.

        Anything inside a grid has X Y coordinates.
        """
        obj.db.coordinates = (0, 0)
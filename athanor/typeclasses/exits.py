import typing
from .mixin import AthanorBase
from evennia.objects.objects import DefaultExit, DefaultObject
from athanor.typing import NAME_TO_ENUM, ExitDir


class AthanorExit(AthanorBase, DefaultExit):
    _content_types = ("exit",)

    def at_object_creation(self):
        super().at_object_creation()
        self.db.direction = NAME_TO_ENUM.get(self.key.lower(), None)

    def at_pre_move(self, destination: typing.Optional[DefaultObject], **kwargs):
        """
        Called just before moving object to destination.
        If returns False, move is cancelled.
        """
        if destination and "room" not in destination._content_types:
            return False
        return True
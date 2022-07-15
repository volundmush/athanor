from evennia import DefaultRoom
from .mixins import AthanorObj
from athanor.dgscripts.dgscripts import DGRoomHandler
from evennia.utils.utils import lazy_property


class AthanorRoom(AthanorObj, DefaultRoom):
    obj_type = "room"

    @lazy_property
    def dgscripts(self):
        return DGRoomHandler(self)
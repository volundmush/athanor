from evennia import DefaultObject
from .mixins import AthanorObj
from athanor.dgscripts.dgscripts import DGItemHandler
from evennia.utils.utils import lazy_property


class AthanorItem(AthanorObj, DefaultObject):
    obj_type = "item"

    @lazy_property
    def dgscripts(self):
        return DGItemHandler(self)

    def at_pre_drop(self, dropper, **kwargs):
        if not self.access(dropper, "drop", default=False):
            dropper.msg(f"You cannot drop {self.get_display_name(dropper)}")
            return False
        if not self.dgscripts.trigger_drop(self, dropper, **kwargs):
            dropper.msg(f"You cannot drop {self.get_display_name(dropper)}")
            return False
        if dropper.location and dropper.location.obj_type == "room":
            if not dropper.location.dgscripts.trigger_drop(self, dropper, **kwargs):
                dropper.msg(f"You cannot drop {self.get_display_name(dropper)} here!")
                return False
        return True


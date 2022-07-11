from evennia import DefaultCharacter
from .mixins import AthanorObj
from athanor.dgscripts.dgscripts import DGMobHandler
from evennia.utils.utils import lazy_property

class AthanorCharacter(AthanorObj, DefaultCharacter):
    obj_type = "character"

    def is_npc(self):
        """
        Anything inheriting from Athanor will want a way to distinguish this!
        """
        return False

    @lazy_property
    def dgscripts(self):
        return DGMobHandler(self)
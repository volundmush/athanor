from evennia.objects.objects import DefaultObject
import athanor
from .mixin import AthanorObject


class AthanorItem(AthanorObject, DefaultObject):
    lock_default_funcs = athanor.OBJECT_OBJECT_DEFAULT_LOCKS
    lockstring = ""

    def basetype_setup(self):
        """
        Overload in order to avoid setting Evennia's default locks.
        """
        pass

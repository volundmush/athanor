from evennia.objects.objects import DefaultObject
import athanor
from .mixin import AthanorObject


class AthanorItem(AthanorObject, DefaultObject):
    lock_default_funcs = athanor.OBJECT_OBJECT_DEFAULT_LOCKS

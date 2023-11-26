from evennia.objects.objects import DefaultExit
import athanor
from .mixin import AthanorObject


class AthanorExit(AthanorObject, DefaultExit):
    lock_default_funcs = athanor.OBJECT_EXIT_DEFAULT_LOCKS

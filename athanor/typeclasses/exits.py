from evennia.objects.objects import DefaultExit
import athanor
from .mixin import AthanorObject


class AthanorExit(AthanorObject, DefaultExit):
    lock_default_funcs = athanor.OBJECT_EXIT_DEFAULT_LOCKS
    lockstring = ""

    def basetype_setup(self):
        """
        Replicates basic basetype_setup,
        but avoids calling super() in order to avoid setting unnecessary locks.
        """
        # an exit should have a destination - try to make sure it does
        if self.location and not self.destination:
            self.destination = self.location

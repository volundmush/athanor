from evennia import DefaultScript
import athanor
from .mixin import AthanorLowBase


class AthanorScript(AthanorLowBase, DefaultScript):
    """
    Base Athanor script all Athanor scripts should inherit from.

    It might do something new eventually.
    """

    lock_access_funcs = athanor.SCRIPT_ACCESS_FUNCTIONS

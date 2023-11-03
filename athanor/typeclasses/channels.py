from evennia.comms.comms import DefaultChannel
import athanor
from .mixin import AthanorAccess


class AthanorChannel(AthanorAccess, DefaultChannel):
    lock_access_funcs = athanor.CHANNEL_ACCESS_FUNCTIONS

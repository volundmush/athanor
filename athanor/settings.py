from evennia.settings_default import *

# Although Athanor makes some changes, we use Multisession mode 3 as a base.
MULTISESSION_MODE = 3

# Remove prefix stripping. We like our @ namespace.
CMD_IGNORE_PREFIXES = ""

# Stores a dict[idstring, details] of all Loopers that'll be
# launched at startup.
# Accepted keys within an idstring are:
# interval - how often to call the callback, in seconds
# callback - a callable function to call
LOOPING_CALLS = {
    "playtime": {
        "interval": 10,
        "callback": "athanor.loopers.playtime",
    }
}

AT_SERVER_STARTSTOP_MODULE = [str(AT_SERVER_STARTSTOP_MODULE),
                              "athanor.startup_hooks"]


SERVER_SESSION_CLASS = "athanor.serversession.AthanorServerSession"

# A list of python modules which will be scanned to generate the
# athanor.MODIFIERS_NAMES and athanor.MODIFIERS_ID dictionaries.
# please see athanor/modifiers.py for more information.
MODIFIER_PATHS = []

ACTION_TEMPLATES = {
    "say": '$You() $conj(say), "{text}"',
    "whisper": '$You() $conj(whisper) to $you(target), "{text}"',
    "pose": '$You() {text}',
    "emit": '{text}',
    "semipose": '$You(){text}',
    "login": '$You() $conj(have) entered the game.',
    "logout": '$You() $conj(have) left the game.'
}

BASE_CHARACTER_TYPECLASS = "athanor.characters.AthanorPlayerCharacter"
BASE_NPC_TYPECLASS = "athanor.characters.AthanorNonPlayerCharacter"
BASE_ITEM_TYPECLASS = "athanor.items.AthanorItem"
BASE_OBJECT_TYPECLASS = BASE_ITEM_TYPECLASS
BASE_ROOM_TYPECLASS = "athanor.rooms.AthanorRoom"
BASE_EXIT_TYPECLASS = "athanor.exits.AthanorExit"
BASE_GRID_TYPECLASS = "athanor.grids.AthanorGrid"
BASE_SECTOR_TYPECLASS = "athanor.sectors.AthanorSector"
BASE_STRUCTURE_TYPECLASS = "athanor.structures.AthanorStructure"

BASE_SCRIPT_TYPECLASS = "athanor.scripts.AthanorScript"

BASE_ACCOUNT_TYPECLASS = "athanor.accounts.AthanorAccount"

BASE_EFFECT_CLASS = "athanor.effects.Effect"

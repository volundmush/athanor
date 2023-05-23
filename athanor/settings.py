from evennia.settings_default import *

MULTISESSION_MODE = 3
AUTO_CREATE_CHARACTER_WITH_ACCOUNT = False
AUTO_PUPPET_ON_LOGIN = False

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

# A list of python modules which will be scanned to generate the
# athanor.ASPECT_CLASSES dictionaries.
# please see athanor/traits.py for more information.
ASPECT_SLOT_CLASS_PATHS = []
ASPECT_CLASS_PATHS = []

QUIRK_SLOT_CLASS_PATHS = []
QUIRK_CLASS_PATHS = []

STAT_CLASS_PATHS = []

EFFECT_COMPONENT_CLASS_PATHS = ["athanor.effect_components"]
EFFECT_CLASS_PATHS = []


ACTION_TEMPLATES = {
    "say": '$You() $conj(say), "{text}"',
    "whisper": '$You() $conj(whisper) to $you(target), "{text}"',
    "pose": '$You() {text}',
    "emit": '{text}',
    "semipose": '$You(){text}',
    "login": '$You() $conj(have) entered the game.',
    "logout": '$You() $conj(have) left the game.'
}

BASE_CHARACTER_TYPECLASS = "athanor.typeclasses.characters.AthanorPlayerCharacter"
BASE_NPC_TYPECLASS = "athanor.typeclasses.characters.AthanorNonPlayerCharacter"
BASE_ITEM_TYPECLASS = "athanor.typeclasses.items.AthanorItem"
BASE_OBJECT_TYPECLASS = BASE_ITEM_TYPECLASS
BASE_ROOM_TYPECLASS = "athanor.typeclasses.rooms.AthanorRoom"
BASE_EXIT_TYPECLASS = "athanor.typeclasses.exits.AthanorExit"
BASE_GRID_TYPECLASS = "athanor.typeclasses.grids.AthanorGrid"
BASE_SECTOR_TYPECLASS = "athanor.typeclasses.sectors.AthanorSector"
BASE_STRUCTURE_TYPECLASS = "athanor.typeclasses.structures.AthanorStructure"

BASE_SCRIPT_TYPECLASS = "athanor.typeclasses.scripts.AthanorScript"

BASE_ACCOUNT_TYPECLASS = "athanor.typeclasses.accounts.AthanorAccount"

BASE_EFFECT_CLASS = "athanor.effects.Effect"

#PORTAL_SESSION_HANDLER_CLASS = "athanor.portalsessions.AthanorPortalSessionHandler"
#SERVER_SESSION_HANDLER_CLASS = "athanor.serversession.AthanorServerSessionHandler"

#TELNET_PROTOCOL_CLASS = "athanor.portalsessions.PlainTelnet"
#SSL_PROTOCOL_CLASS = "athanor.portalsessions.SecureTelnet"
#SSH_PROTOCOL_CLASS = "athanor.portalsessions.SSHProtocol"
#WEBSOCKET_PROTOCOL_CLASS = "athanor.portalsessions.WebSocket"


PROMPT_ENABLED = True
PROMPT_DELAY = 0.1

AUTOMAP_ENABLED = True


DUB_SYSTEM_ENABLED = False

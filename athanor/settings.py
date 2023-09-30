from evennia.settings_default import *

MULTISESSION_MODE = 3
AUTO_CREATE_CHARACTER_WITH_ACCOUNT = False
AUTO_PUPPET_ON_LOGIN = False
MAX_NR_SIMULTANEOUS_PUPPETS = 10
MAX_NR_CHARACTERS = 10

# Remove prefix stripping. We like our @ namespace.
CMD_IGNORE_PREFIXES = ""

AT_SERVER_STARTSTOP_MODULE = [AT_SERVER_STARTSTOP_MODULE] if isinstance(AT_SERVER_STARTSTOP_MODULE, str) else AT_SERVER_STARTSTOP_MODULE
AT_SERVER_STARTSTOP_MODULE.append("athanor.startup_hooks")

# A list of python modules which will be scanned to generate the
# athanor.ASPECT_CLASSES dictionaries.
# please see athanor/traits.py for more information.


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


BASE_SCRIPT_TYPECLASS = "athanor.typeclasses.scripts.AthanorScript"

BASE_ACCOUNT_TYPECLASS = "athanor.typeclasses.accounts.AthanorAccount"


PROMPT_ENABLED = False
PROMPT_DELAY = 0.1

AUTOMAP_ENABLED = False


DUB_SYSTEM_ENABLED = False

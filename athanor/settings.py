from evennia.settings_default import *
from collections import defaultdict as _ddict


INSTALLED_APPS.extend([
    "athanor.plays",
    "athanor.dgscripts"

])


SYSTEMS = [
    "athanor.systems.CmdQueueSystem",
    "athanor.systems.PlaySystem",
    "athanor.systems.DGWaitSystem",
    "athanor.systems.DGResetSystem",
    "athanor.systems.DGRandomSystem"
]

MODIFIER_PATHS = []

MULTISESSION_MODE = 3
# The maximum number of characters allowed by the default ooc char-creation command

CMD_IGNORE_PREFIXES = ""

SERVER_SESSION_CLASS = "athanor.serversession.AthanorSession"
BASE_PLAY_TYPECLASS = "athanor.plays.plays.DefaultPlay"
BASE_DGSCRIPT_TYPECLASS = "athanor.dgscripts.dgscripts.DefaultDGScript"

CMDSET_PLAY = "athanor.commands.cmdsets.PlayCmdSet"

AT_SERVER_STARTSTOP_MODULE = "athanor.server_hooks"

# The number of characters that can be logged-in per account simultaneously. Builder permissions override this.
PLAYS_PER_ACCOUNT = 1

# Used as a location if both sending to logout location and home fails.
SAFE_FALLBACK = DEFAULT_HOME

# Number of seconds a Play session can go without Sessions before it's
# forcibly terminated.
PLAY_TIMEOUT_SECONDS = 30.0

INPUT_FUNC_MODULES.insert(1, "athanor.inputfuncs")

DG_INSTANCE_CLASSES = {
    "item": "athanor.dgscripts.dgscripts.DGScriptItemInstance",
    "character": "athanor.dgscripts.dgscripts.DGScriptCharacterInstance",
    "room": "athanor.dgscripts.dgscripts.DGScriptRoomInstance"
}

DG_VARS = [
    "athanor.dgscripts.dgvars"
]

DG_FUNCTIONS = _ddict(list)
DG_FUNCTIONS["shared"].extend([
    "athanor.dgscripts.dgfuncs"
])
DG_FUNCTIONS["character"].extend([

])
DG_FUNCTIONS["item"].extend([

])
DG_FUNCTIONS["room"].extend([

])

EQUIP_CLASS_PATHS = [
    "athanor.equip"
]

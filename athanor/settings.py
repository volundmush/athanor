from evennia.settings_default import *

INSTALLED_APPS.extend([
    "athanor.plays",

])


SYSTEMS = [
    "athanor.systems.CmdQueueSystem"
]

MODIFIER_PATHS = []

MULTISESSION_MODE = 3
# The maximum number of characters allowed by the default ooc char-creation command
MAX_NR_CHARACTERS = 10

CMD_IGNORE_PREFIXES = ""

SERVER_SESSION_CLASS = "athanor.serversession.AthanorSession"
BASE_PLAY_TYPECLASS = "athanor.plays.plays.DefaultPlay"
BASE_DGSCRIPT_TYPECLASS = "athanor.dgscripts.dgscripts.DefaultDGScript"

CMDSET_PLAY = "athanor.commands.cmdsets.PlayCmdSet"

AT_SERVER_STARTSTOP_MODULE = "athanor.server_hooks"

# The number of characters that can be logged-in per account simultaneously. Builder permissions override this.
PLAYS_PER_ACCOUNT = 1


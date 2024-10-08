from django.dispatch import Signal
from collections import defaultdict

CHARACTERS_ONLINE = set()

CMDSETS_UNLOGGEDIN_EXTRA = []
CMDSETS_SESSION_EXTRA = []
CMDSETS_CHARACTER_EXTRA = []
CMDSETS_ACCOUNT_EXTRA = []

CMD_MODULES_UNLOGGEDIN = []
CMD_MODULES_SESSION = []
CMD_MODULES_CHARACTER = []
CMD_MODULES_ACCOUNT = []

PLUGINS = dict()

OBJECT_ACCESS_FUNCTIONS = defaultdict(list)
SCRIPT_ACCESS_FUNCTIONS = defaultdict(list)
ACCOUNT_ACCESS_FUNCTIONS = defaultdict(list)
CHANNEL_ACCESS_FUNCTIONS = defaultdict(list)

EVENTS: dict[str, Signal] = defaultdict(Signal)

OBJECT_OBJECT_DEFAULT_LOCKS = defaultdict(list)
OBJECT_CHARACTER_DEFAULT_LOCKS = defaultdict(list)
OBJECT_EXIT_DEFAULT_LOCKS = defaultdict(list)
OBJECT_ROOM_DEFAULT_LOCKS = defaultdict(list)
ACCOUNT_DEFAULT_LOCKS = defaultdict(list)

HANDLERS = defaultdict(dict)


def _apply_settings(settings):

    settings.BASE_CHARACTER_TYPECLASS = (
        "athanor.typeclasses.characters.AthanorCharacter"
    )

    settings.BASE_ITEM_TYPECLASS = "athanor.typeclasses.items.AthanorItem"
    settings.BASE_OBJECT_TYPECLASS = settings.BASE_ITEM_TYPECLASS
    settings.BASE_ROOM_TYPECLASS = "athanor.typeclasses.rooms.AthanorRoom"
    settings.BASE_EXIT_TYPECLASS = "athanor.typeclasses.exits.AthanorExit"

    settings.BASE_SCRIPT_TYPECLASS = "athanor.typeclasses.scripts.AthanorScript"

    settings.BASE_ACCOUNT_TYPECLASS = "athanor.typeclasses.accounts.AthanorAccount"

    settings.BASE_CHANNEL_TYPECLASS = "athanor.typeclasses.channels.AthanorChannel"

    settings.CMDSET_UNLOGGEDIN = "athanor.cmdsets.UnloggedinCmdSet"
    settings.CMDSET_SESSION = "athanor.cmdsets.SessionCmdSet"
    settings.CMDSET_CHARACTER = "athanor.cmdsets.CharacterCmdSet"
    settings.CMDSET_ACCOUNT = "athanor.cmdsets.AccountCmdSet"

    settings.CMDSETS_UNLOGGEDIN_EXTRA = []
    settings.CMDSETS_SESSION_EXTRA = []
    settings.CMDSETS_CHARACTER_EXTRA = []
    settings.CMDSETS_ACCOUNT_EXTRA = []

    settings.CMD_MODULES_UNLOGGEDIN = []
    settings.CMD_MODULES_SESSION = []
    settings.CMD_MODULES_CHARACTER = ["athanor.commands.characters"]
    settings.CMD_MODULES_ACCOUNT = ["athanor.commands.accounts"]

    settings.AUTOMAP_ENABLED = False

    settings.ALERTS_CHANNEL = "MudInfo"
    settings.ROOT_URLCONF = "athanor.urls"

    settings.URL_INCLUDES = [
        ("", "web.website.urls"),
        ("webclient/", "web.webclient.urls"),
        ("admin/", "web.admin.urls"),
        ("athanor/", "athanor.website.urls"),
    ]

    settings.DJANGO_ADMIN_APP_ORDER = [
        "accounts",
        "objects",
        "scripts",
        "comms",
        "help",
        "typeclasses",
        "server",
        "sites",
        "flatpages",
        "auth",
    ]

    settings.DJANGO_ADMIN_APP_EXCLUDE = ["account"]

    settings.HELP_MORE_ENABLED = False

    settings.OBJECT_ACCESS_FUNCTIONS = defaultdict(list)
    settings.SCRIPT_ACCESS_FUNCTIONS = defaultdict(list)
    settings.ACCOUNT_ACCESS_FUNCTIONS = defaultdict(list)
    settings.CHANNEL_ACCESS_FUNCTIONS = defaultdict(list)

    settings.ACCESS_FUNCTIONS_LIST = ["OBJECT", "SCRIPT", "ACCOUNT", "CHANNEL"]

    settings.OBJECT_OBJECT_DEFAULT_LOCKS = defaultdict(list)
    settings.OBJECT_CHARACTER_DEFAULT_LOCKS = defaultdict(list)
    settings.OBJECT_EXIT_DEFAULT_LOCKS = defaultdict(list)
    settings.OBJECT_ROOM_DEFAULT_LOCKS = defaultdict(list)
    settings.ACCOUNT_DEFAULT_LOCKS = defaultdict(list)

    account_default_locks = {
        "boot": "perm(Admin)",
        "examine": "perm(Admin)",
        "edit": "perm(Admin)",
        "delete": "perm(Developer)",
        "msg": "true()",
        "noidletimeout": "perm(Admin)",
    }

    object_default_locks = {
        "control": "perm(Developer)",
        "examine": "perm(Builder)",
        "edit": "perm(Admin)",
        "delete": "perm(Admin)",
        "get": "all()",
        "drop": "holds()",
        "call": "true()",
        "tell": "perm(Admin)",
        "puppet": "pperm(Developer)",
        "teleport": "true()",
        "teleport_here": "true()",
        "view": "all()",
        "noidletimeout": "perm(Builder) or perm(noidletimeout)",
    }

    character_default_locks = object_default_locks.copy()
    character_default_locks.update(
        {
            "get": "false()",
            "call": "false()",
            "teleport": "perm(Admin)",
            "teleport_here": "perm(Admin)",
        }
    )

    room_default_locks = object_default_locks.copy()
    room_default_locks.update(
        {
            "get": "false()",
            "puppet": "false()",
            "teleport": "false()",
            "teleport_here": "true()",
        }
    )

    exit_default_locks = object_default_locks.copy()
    exit_default_locks.update(
        {
            "traverse": "all()",
            "get": "false()",
            "puppet": "false()",
            "teleport": "false()",
            "teleport_here": "false()",
        }
    )

    for locks, target in [
        (object_default_locks, settings.OBJECT_OBJECT_DEFAULT_LOCKS),
        (character_default_locks, settings.OBJECT_CHARACTER_DEFAULT_LOCKS),
        (room_default_locks, settings.OBJECT_ROOM_DEFAULT_LOCKS),
        (exit_default_locks, settings.OBJECT_EXIT_DEFAULT_LOCKS),
        (account_default_locks, settings.ACCOUNT_DEFAULT_LOCKS),
    ]:
        for k, v in locks.items():
            target[k].append(v)

    settings.DEFAULT_LOCKS_LIST = [
        "OBJECT_OBJECT",
        "OBJECT_CHARACTER",
        "OBJECT_EXIT",
        "OBJECT_ROOM",
        "ACCOUNT",
    ]

    # if True, characters who go offline will be stowed in Nowhere and brought back when they next login.
    # if False, they will remain in the rooms, but simply are offline. It's best to use room formatters to
    # hide them?
    settings.OFFLINE_CHARACTERS_VOID_STORAGE = True

    settings.ATHANOR_HANDLERS = defaultdict(dict)

    settings.COMMAND_DEFAULT_CLASS = "athanor.commands.AthanorCommand"

    # The number of seconds to wait between each call to the playtime command.
    # This is also how many seconds will be added to playtime.
    settings.PLAYTIME_INTERVAL = 1



    settings.PERMISSION_HIERARCHY = [
        "Guest",  # note-only used if GUEST_ENABLED=True
        "Player",
        "Helper",
        "Gamemaster",  # Added in Athanor.
        "Builder",
        "Admin",
        "Developer",
    ]


def init(settings, plugins=None):
    _apply_settings(settings)

    if plugins is None:
        plugins = list()

    from importlib import import_module

    call_order = list()
    for plugin in plugins:
        module = import_module(plugin)

        if hasattr(module, "init"):
            PLUGINS[plugin] = module
            call_order.append(module)

    for p in call_order:
        p.init(settings, PLUGINS)

    for p in call_order:
        if callable((post_init := getattr(p, "post_init", None))):
            post_init(settings, PLUGINS)


def finalize(settings):
    for p in PLUGINS.values():
        if callable((finalize := getattr(p, "finalize", None))):
            finalize(settings, PLUGINS)

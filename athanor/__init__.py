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

EVENTS: dict[str, set] = defaultdict(set)


def emit(event: str, *args, **kwargs):
    callbacks = EVENTS.get(event, set())
    for callback in callbacks:
        callback(*args, **kwargs)


def register_event(event: str, callback):
    EVENTS[event].add(callback)


def unregister_event(event: str, callback):
    if event in EVENTS:
        EVENTS[event].remove(callback)


def _apply_settings(settings):
    settings.MULTISESSION_MODE = 3
    settings.AUTO_CREATE_CHARACTER_WITH_ACCOUNT = False
    settings.AUTO_PUPPET_ON_LOGIN = False
    settings.MAX_NR_SIMULTANEOUS_PUPPETS = 10
    settings.MAX_NR_CHARACTERS = 10

    settings.AT_SERVER_STARTSTOP_MODULE = (
        [settings.AT_SERVER_STARTSTOP_MODULE]
        if isinstance(settings.AT_SERVER_STARTSTOP_MODULE, str)
        else settings.AT_SERVER_STARTSTOP_MODULE
    )
    settings.AT_SERVER_STARTSTOP_MODULE.append("athanor.startup_hooks")

    settings.ACTION_TEMPLATES = {
        "say": '$You() $conj(say), "{text}"',
        "whisper": '$You() $conj(whisper) to $you(target), "{text}"',
        "pose": "$You() {text}",
        "emit": "{text}",
        "semipose": "$You(){text}",
        "login": "$You() $conj(have) entered the game.",
        "logout": "$You() $conj(have) left the game.",
    }

    settings.BASE_CHARACTER_TYPECLASS = (
        "athanor.typeclasses.characters.AthanorPlayerCharacter"
    )
    settings.BASE_NPC_TYPECLASS = (
        "athanor.typeclasses.characters.AthanorNonPlayerCharacter"
    )
    settings.BASE_ITEM_TYPECLASS = "athanor.typeclasses.items.AthanorItem"
    settings.BASE_OBJECT_TYPECLASS = settings.BASE_ITEM_TYPECLASS
    settings.BASE_ROOM_TYPECLASS = "athanor.typeclasses.rooms.AthanorRoom"
    settings.BASE_EXIT_TYPECLASS = "athanor.typeclasses.exits.AthanorExit"

    settings.BASE_SCRIPT_TYPECLASS = "athanor.typeclasses.scripts.AthanorScript"

    settings.BASE_ACCOUNT_TYPECLASS = "athanor.typeclasses.accounts.AthanorAccount"

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
    settings.CMD_MODULES_CHARACTER = []
    settings.CMD_MODULES_ACCOUNT = []

    settings.AUTOMAP_ENABLED = False

    settings.OPTIONS_ACCOUNT_DEFAULT["screenreader"] = (
        "Minimize fancy formatting.",
        "Boolean",
        False,
    )
    settings.OPTIONS_ACCOUNT_DEFAULT["border_color"] = (
        "Headers, footers, table borders, etc.",
        "Color",
        "M",
    )
    settings.OPTIONS_ACCOUNT_DEFAULT["header_text_color"] = (
        "Text inside Header lines.",
        "Color",
        "w",
    )
    settings.OPTIONS_ACCOUNT_DEFAULT["client_width"] = (
        "Preferred client width.",
        "PositiveInteger",
        settings.CLIENT_DEFAULT_WIDTH
    )
    # ROOT_URLCONF = "athanor.urls"

    settings.ALERTS_CHANNELS = "MudInfo"


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

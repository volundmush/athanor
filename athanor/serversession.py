from django.conf import settings
from rich.color import ColorSystem
from twisted.internet.defer import inlineCallbacks, returnValue
from evennia.server.serversession import ServerSession, _BASE_SESSION_CLASS
from athanor.plays.plays import DefaultPlay
from evennia.utils.utils import make_iter, lazy_property, class_from_module

_ObjectDB = None
_PlayTC = None
_Select = None


class AthanorSession(ServerSession):
    cmd_objects_sort_priority = 0

    def __init__(self):
        super().__init__()
        self.play = None

    @lazy_property
    def console(self):
        from mudrich import MudConsole
        if "SCREENWIDTH" in self.protocol_flags:
            width = self.protocol_flags["SCREENWIDTH"][0]
        else:
            width = 78
        return MudConsole(color_system=self.rich_color_system(), width=width,
                          file=self, record=True)

    def rich_color_system(self):
        if self.protocol_flags.get("NOCOLOR", False):
            return None
        if self.protocol_flags.get("XTERM256", False):
            return "256"
        if self.protocol_flags.get("ANSI", False):
            return "standard"
        return None

    def update_rich(self):
        check = self.console
        if "SCREENWIDTH" in self.protocol_flags:
            self.console._width = self.protocol_flags["SCREENWIDTH"][0]
        else:
            self.console._width = 80
        if self.protocol_flags.get("NOCOLOR", False):
            self.console._color_system = None
        elif self.protocol_flags.get("XTERM256", False):
            self.console._color_system = ColorSystem.EIGHT_BIT
        elif self.protocol_flags.get("ANSI", False):
            self.console._color_system = ColorSystem.STANDARD

    def write(self, b: str):
        """
        When self.console.print() is called, it writes output to here.
        Not necessarily useful, but it ensures console print doesn't end up sent out stdout or etc.
        """

    def flush(self):
        """
        Do not remove this method. It's needed to trick Console into treating this object
        as a file.
        """

    def print(self, *args, **kwargs) -> str:
        """
        A thin wrapper around Rich.Console's print. Returns the exported data.
        """
        self.console.print(*args, highlight=False, **kwargs)
        return self.console.export_text(clear=True, styles=True)

    def msg(self, text=None, **kwargs):
        if text is not None:
            if hasattr(text, "__rich_console__"):
                text = self.print(text)
        super().msg(text=text, **kwargs)

    def data_out(self, **kwargs):
        if (t := kwargs.get("text", None)):
            if hasattr(t, "__rich_console__"):
                kwargs["text"] = self.print(t)
        super().data_out(**kwargs)

    def get_cmd_objects(self):
        cmd_objects = {"session": self}
        if self.play:
            cmd_objects.update(self.play.get_cmd_objects())
        else:
            if self.account:
                cmd_objects["account"] = self.account
        return cmd_objects

    @inlineCallbacks
    def get_extra_cmdsets(self, caller, current, cmdsets):
        """
        Called by the CmdHandler to retrieve extra cmdsets from this object.
        Evennia doesn't have any by default for Sessions, but you can
        overload and add some.
        """
        out = yield list()
        return out

    def at_sync(self):
        """
        Making some slight adjustments to support Play objects.
        """
        global _ObjectDB
        if not _ObjectDB:
            from evennia.objects.models import ObjectDB as _ObjectDB

        _BASE_SESSION_CLASS.at_sync(self)
        if not self.logged_in:
            # assign the unloggedin-command set.
            self.cmdset_storage = settings.CMDSET_UNLOGGEDIN

        self.cmdset.update(init_mode=True)

        if self.puid:
            # reconnect puppet (puid is only set if we are coming
            # back from a server reload). This does all the steps
            # done in the default @ic command but without any
            # hooks, echoes or access checks.

            # PLAY UPDATE: PlayDB pks use ObjectID PKs, so we can
            # slip in some changes here.

            play = DefaultPlay.objects.get(id=self.puid)
            play.add_session(self)

    def get_puppet(self):
        """
        Get the in-game character associated with this session.

        Returns:
            puppet (Object): The puppeted object, if any.

        """
        if self.play:
            return self.play.id
        return None

    def get_puppet_or_account(self):
        if self.logged_in:
            if self.play:
                return self.play.id
            else:
                return self.account
        return None

    def load_sync_data(self, sessdata):
        super().load_sync_data(sessdata)
        self.update_rich()

    def create_or_join_play(self, obj):
        if self.play:
            raise RuntimeError("This session is already controlling a character!")
        if not self.account:
            raise RuntimeError("Must be logged in.")
        if not obj:
            raise RuntimeError("Object not found.")
        if (play := obj.get_play()):
            if play.account != self.account:
                raise RuntimeError("Character is in play by another account!")
            play.add_session(self)
            play.on_additional_session(self)
        else:
            # object is not in play, so we'll start a new play for it.
            global _PlayTC
            if not _PlayTC:
                _PlayTC = class_from_module(settings.BASE_PLAY_TYPECLASS)
            existing = self.account.plays.count()
            if existing >= settings.PLAYS_PER_ACCOUNT and not self.locks.check_lockstring(self, "perm(Builder)"):
                raise RuntimeError(f"You have reached the maximum of {settings.PLAYS_PER_ACCOUNT} characters in play.")
            new_play = _PlayTC.create(self.account, obj)
            new_play.add_session(self)
            new_play.on_first_session(self)
            new_play.at_start()

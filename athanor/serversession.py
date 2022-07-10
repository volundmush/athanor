from django.conf import settings
from rich.color import ColorSystem

from evennia.server.serversession import ServerSession
from athanor.plays.plays import DefaultPlay
from evennia.utils.utils import make_iter, lazy_property, class_from_module

_ObjectDB = None
_PlayTC = None
_Select = None


class AthanorSession(ServerSession):

    def __init__(self):
        super().__init__()
        self.play = None

    @lazy_property
    def console(self):
        from mudrich import MudConsole
        return MudConsole(color_system=self.rich_color_system(), width=self.protocol_flags["SCREENWIDTH"][0],
                          file=self, record=True)

    def rich_color_system(self):
        if self.protocol_flags["NOCOLOR"]:
            return None
        if self.protocol_flags["XTERM256"]:
            return "256"
        if self.protocol_flags["ANSI"]:
            return "standard"

    def update_rich(self):
        self.console._width = self.protocol_flags["SCREENWIDTH"][0]
        if self.protocol_flags["NOCOLOR"]:
            self.console._color_system = None
        elif self.protocol_flags["XTERM256"]:
            self.console._color_system = ColorSystem.EIGHT_BIT
        elif self.protocol_flags["ANSI"]:
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
            if self.puppet:
                self.prompt.prepare()
        super().data_out(**kwargs)

    @lazy_property
    def prompt(self):
        return PromptHandler(self)

    def get_cmd_objects(self):
        cmd_objects = super().get_cmd_objects()
        if self.play:
            cmd_objects["play"] = self.play
        return cmd_objects

    def at_sync(self):
        """
        Making some slight adjustments to support Play objects.
        """
        global _ObjectDB
        if not _ObjectDB:
            from evennia.objects.models import ObjectDB as _ObjectDB

        super().at_sync()
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
            self.bind_to_play(play)

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

    def bind_to_play(self, play):
        play.sessions.add(self)
        self.play = play
        self.puid = obj.id

    def create_or_join_play(self, obj):
        if self.play:
            raise RuntimeError("This session is already controlling a character!")
        if not self.account:
            raise RuntimeError("Must be logged in.")
        if not obj:
            raise RuntimeError("Object not found.")
        if hasattr(obj, "play"):
            # object is already in play. We can just join it.
            play = obj.play
            if play.account != self.account:
                raise RuntimeError("Character is in play by another account!")
            self.bind_to_play(play)
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
            self.bind_to_play(new_play)
            new_play.on_first_session(self)
            new_play.at_start()

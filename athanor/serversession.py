from rich.color import ColorSystem
from django.conf import settings
from evennia.server.sessionhandler import ServerSessionHandler, codecs_decode, _ERR_BAD_UTF8,\
    _FUNCPARSER_PARSE_OUTGOING_MESSAGES_ENABLED, is_iter
from evennia.server.serversession import ServerSession
from evennia.utils.utils import lazy_property, logger

_FUNCPARSER = None

_ObjectDB = None
_PlayTC = None
_Select = None


class AthanorServerSession(ServerSession):

    @lazy_property
    def console(self):
        #from athanor.mudrich import MudConsole
        from rich.console import Console as MudConsole
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
            check._width = self.protocol_flags["SCREENWIDTH"][0]
        else:
            check._width = 80
        if self.protocol_flags.get("NOCOLOR", False):
            check._color_system = None
        elif self.protocol_flags.get("XTERM256", False):
            check._color_system = ColorSystem.EIGHT_BIT
        elif self.protocol_flags.get("ANSI", False):
            check._color_system = ColorSystem.STANDARD

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

    def data_out(self, **kwargs):
        """
        A second check to ensure that all uses of "rich" are getting processed properly.
        """
        if (r := kwargs.get("rich", None)) and hasattr(r, "__rich_console__"):
            kwargs["rich"] = self.print(r)
        super().data_out(**kwargs)

    def load_sync_data(self, sessdata):
        super().load_sync_data(sessdata)
        self.update_rich()

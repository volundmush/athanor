from rich.color import ColorSystem
from evennia.server.serversession import ServerSession
from evennia.utils.utils import lazy_property
from evennia.utils.ansi import parse_ansi, ANSIString
from evennia.utils.text2html import parse_html

_ObjectDB = None
_PlayTC = None
_Select = None


class AthanorServerSession(ServerSession):

    @lazy_property
    def console(self):
        from athanor.mudrich import MudConsole
        if "SCREENWIDTH" in self.protocol_flags:
            width = self.protocol_flags["SCREENWIDTH"][0]
        else:
            width = 78
        return MudConsole(color_system=self.rich_color_system(), width=width,
                          file=self, record=True)

    def rich_color_system(self):
        if self.protocol_flags.get("NOCOLOR", False):
            return None
        if self.is_webclient():
            return "truecolor"
        if self.protocol_flags.get("TRUECOLOR", False):
            return "256"
        if self.protocol_flags.get("XTERM256", False):
            return "256"
        if self.protocol_flags.get("ANSI", False):
            return "standard"
        return None

    def is_webclient(self):
        return self.protocol_flags.get("CLIENTNAME", "").startswith("Evennia Webclient")

    def update_rich(self):
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

    def fileno(self):
        return -1

    def print(self, text) -> str:
        """
        A thin wrapper around Rich.Console's print. Returns the exported data.
        """
        self.console.print(text, highlight=False)
        return self.console.export_text(clear=True, styles=True)

    def repr(self, text):
        """
        A thin wrapper around Rich.Console's print. Returns the exported data.
        """
        self.console.print(text)
        return self.console.export_text(clear=True, styles=True)

    def load_sync_data(self, sessdata):
        super().load_sync_data(sessdata)
        self.update_rich()
from rich.color import ColorSystem
from rich.console import Console
from django.conf import settings
from evennia.server.portal.telnet import TelnetProtocol
from evennia.server.portal.ssh import SshProtocol
from evennia.server.portal.webclient import WebSocketClient

from evennia.utils.utils import lazy_property
from evennia.utils.logger import log_trace

from athanor.ansi import RavensGleaning


class AthanorPortalSession:
    def get_width(self):
        if "SCREENWIDTH" in self.protocol_flags:
            return self.protocol_flags["SCREENWIDTH"][0]
        return settings.CLIENT_DEFAULT_WIDTH

    @lazy_property
    def console(self):
        return Console(
            color_system=self.rich_color_system(),
            width=self.get_width(),
            file=self,
            record=True,
            mxp=self.protocol_flags.get("MXP", False),
        )

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
        check._width = self.get_width()
        if self.protocol_flags.get("NOCOLOR", False):
            check._color_system = None
        elif self.protocol_flags.get("XTERM256", False):
            check._color_system = ColorSystem.EIGHT_BIT
        elif self.protocol_flags.get("ANSI", False):
            check._color_system = ColorSystem.STANDARD
        check._mxp = self.protocol_flags.get("MXP", False)

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
        new_kwargs = {"highlight": False}
        new_kwargs.update(kwargs)
        self.console.print(*args, **new_kwargs)
        output = self.console.export_text(clear=True, styles=True)
        return output

    def print_html(self, *args, **kwargs) -> str:
        """
        A thin wrapper around Rich.Console's print. Returns the exported data.
        """
        new_kwargs = {"highlight": False}
        new_kwargs.update(kwargs)
        self.console.print(*args, **new_kwargs)
        output = self.console.export_html(clear=True, inline_styles=True)
        return output

    def load_sync_data(self, sessdata):
        self.at_portal_sync()
        return super().load_sync_data(sessdata)

    def at_portal_sync(self):
        self.update_rich()

    def send_ansi(self, *args, **kwargs):
        """
        Send raw data as ANSI color. args[0] should already be
        fully rendered.
        """
        if not args:
            return
        if not isinstance(args[0], str):
            return
        options = dict(kwargs.get("options", dict()))
        options["raw"] = True
        kwargs["options"] = options
        self.send_text(*args, **kwargs)


class PlainTelnet(AthanorPortalSession, TelnetProtocol):
    render_types = ("ansi", "oob")

    def handle_sendables_ansi(self, sendables, metadata):
        print(f"{self} got ANSI sendables: {sendables} with metadata: {metadata}")
        print(f"{self} protocol_flags are: {self.protocol_flags}")
        print(f"{self} console MXP: {self.console._mxp}")
        for sendable in sendables:
            if callable(method := getattr(sendable, "render_as_ansi", None)):
                try:
                    output = method(self, metadata)
                    print(f"{self} got ANSI output from {sendable}: {output}")
                    self.send_ansi(*[output], **metadata)
                except Exception:
                    log_trace()
            else:
                print(f"{self} got ANSI sendable with no render_as_ansi: {sendable}")


class SecureTelnet(PlainTelnet):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.protocol_key = "telnet/ssl"


class SSHProtocol(AthanorPortalSession, SshProtocol):
    pass


class WebSocket(AthanorPortalSession, WebSocketClient):
    converter = RavensGleaning()

    def send_ansi(self, *args, **kwargs):
        """
        Send rich data as ANSI color. args[0] should already be
        fully rendered.
        """
        if not args:
            return
        if not isinstance(args[0], str):
            return
        html = self.converter.convert(args[0])
        new_args = [html]
        new_args.extend(args[1:])
        options = dict(kwargs.get("options", dict()))
        options["raw"] = True
        options["client_raw"] = True
        kwargs["options"] = options

        self.send_text(*new_args, **kwargs)

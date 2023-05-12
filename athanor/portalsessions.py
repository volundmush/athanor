from rich.color import ColorSystem
from evennia.utils.utils import lazy_property
from evennia.server.portal.telnet import TelnetProtocol, IAC, GA, to_bytes, mccp_compress, _RE_SCREENREADER_REGEX

from evennia.server.portal.ssh import SshProtocol
from evennia.server.portal.webclient import WebSocketClient, json

from evennia.server.portal.portalsessionhandler import PortalSessionHandler
from evennia.utils.ansi import ANSIString
from athanor.mudrich import EvToRich, install_mudrich
from rich.highlighter import NullHighlighter, ReprHighlighter

from bs4 import BeautifulSoup


class AthanorPortalSessionHandler(PortalSessionHandler):

    def __init__(self, *args, **kwargs):
        install_mudrich()
        super().__init__(*args, **kwargs)

    def sync(self, session):
        """
        A simple override so that sessions can tell their Rich Consoles
        to update when their settings have changed.
        """
        super().sync(session)
        session.at_portal_sync()

    def convert_rich(self, text):
        if isinstance(text, ANSIString):
            return EvToRich(text)
        elif hasattr(text, "__rich_console__"):
            return text
        elif isinstance(text, str):
            return EvToRich(text)
        return text

    def data_out(self, session, **kwargs):
        if not session:
            return
        if (text_kw := kwargs.get("text", None)):
            cmdargs, cmdkwargs = text_kw
            if cmdargs:
                text = cmdargs[0]
                cmdargs[0] = self.convert_rich(text)
                kwargs["text"] = (cmdargs, cmdkwargs)
        super().data_out(session, **kwargs)


class PortalSessionMixin:

    def at_portal_sync(self):
        self.update_rich()

    def get_clientname(self):
        return self.protocol_flags.get("CLIENTNAME", "Unknown")

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
            return "truecolor"
        if self.protocol_flags.get("XTERM256", False):
            return "256"
        if self.protocol_flags.get("ANSI", False):
            return "standard"
        return None

    def is_webclient(self):
        return self.get_clientname().startswith("Evennia Webclient")

    def update_width(self):
        if "SCREENWIDTH" in self.protocol_flags:
            self.console._width = self.protocol_flags["SCREENWIDTH"][0]
        else:
            self.console._width = 80

    def update_rich(self):
        self.update_width()
        if self.protocol_flags.get("NOCOLOR", False):
            self.console._color_system = None
        elif self.protocol_flags.get("TRUECOLOR", False):
            self.console._color_system = ColorSystem.TRUECOLOR
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

    def print(self, text, styles=True, highlight=False) -> str:
        """
        A thin wrapper around Rich.Console's print. Returns the exported data.
        """
        self.console.print(text, highlight=highlight)
        return self.console.export_text(clear=True, styles=styles)


class PlainTelnet(TelnetProtocol, PortalSessionMixin):

    def send_text(self, *args, **kwargs):
        """
        Send text data. This is an in-band telnet operation.

        Args:
            text (str): The first argument is always the text string to send. No other arguments
                are considered.
        Keyword Args:
            options (dict): Send-option flags

               - mxp: Enforce MXP link support.
               - ansi: Enforce no ANSI colors.
               - xterm256: Enforce xterm256 colors, regardless of TTYPE.
               - noxterm256: Enforce no xterm256 color support, regardless of TTYPE.
               - nocolor: Strip all Color, regardless of ansi/xterm256 setting.
               - raw: Pass string through without any ansi processing
                    (i.e. include Evennia ansi markers but do not
                    convert them into ansi tokens)
               - echo: Turn on/off line echo on the client. Turn
                    off line echo for client, for example for password.
                    Note that it must be actively turned back on again!

        """
        text = args[0] if args else ""
        if text is None:
            return

        # handle arguments
        options = kwargs.get("options", {})
        flags = self.protocol_flags
        # xterm256 = options.get("xterm256", flags.get("XTERM256", False) if flags.get("TTYPE", False) else True)
        # useansi = options.get("ansi", flags.get("ANSI", False) if flags.get("TTYPE", False) else True)
        raw = options.get("raw", flags.get("RAW", False))
        # nocolor = options.get("nocolor", flags.get("NOCOLOR") or not (xterm256 or useansi))
        # echo = options.get("echo", None)
        # mxp = options.get("mxp", flags.get("MXP", False))
        screenreader = options.get("screenreader", flags.get("SCREENREADER", False))
        highlight = options.get("highlight", False)

        rendered = text if raw else self.print(text, styles=not raw, highlight=highlight)
        if screenreader:
            rendered = _RE_SCREENREADER_REGEX.sub("", text)
        if options.get("send_prompt"):
            prompt = to_bytes(rendered, self)
            prompt = prompt.replace(IAC, IAC + IAC).replace(b"\n", b"\r\n")
            if not self.protocol_flags.get(
                    "NOPROMPTGOAHEAD", self.protocol_flags.get("NOGOAHEAD", True)
            ):
                prompt += IAC + GA
            self.transport.write(mccp_compress(self, prompt))
        else:
            self.sendLine(rendered)


class SecureTelnet(PlainTelnet):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.protocol_key = "telnet/ssl"


class SSHProtocol(SshProtocol, PortalSessionMixin):

    def update_width(self):
        self.console._width = self.width
        self.console._height = self.height

    def send_text(self, *args, **kwargs):
        """
        Send text data. This is an in-band telnet operation.

        Args:
            text (str): The first argument is always the text string to send. No other arguments
                are considered.
        Keyword Args:
            options (dict): Send-option flags (booleans)

                - mxp: enforce mxp link support.
                - ansi: enforce no ansi colors.
                - xterm256: enforce xterm256 colors, regardless of ttype setting.
                - nocolor: strip all colors.
                - raw: pass string through without any ansi processing
                  (i.e. include evennia ansi markers but do not
                  convert them into ansi tokens)
                - echo: turn on/off line echo on the client. turn
                  off line echo for client, for example for password.
                  note that it must be actively turned back on again!

        """
        # print "telnet.send_text", args,kwargs  # DEBUG
        text = args[0] if args else ""
        if text is None:
            return

        # handle arguments
        options = kwargs.get("options", {})
        flags = self.protocol_flags
        xterm256 = options.get("xterm256", flags.get("XTERM256", True))
        useansi = options.get("ansi", flags.get("ANSI", True))
        raw = options.get("raw", flags.get("RAW", False))
        nocolor = options.get("nocolor", flags.get("NOCOLOR") or not (xterm256 or useansi))
        # echo = options.get("echo", None)  # DEBUG
        screenreader = options.get("screenreader", flags.get("SCREENREADER", False))
        highlight = options.get("highlight", False)

        rendered = text if raw else self.print(text, styles=not raw, highlight=True)

        if screenreader:
            # screenreader mode cleans up output
            rendered = _RE_SCREENREADER_REGEX.sub("", rendered)

        self.sendLine(rendered)


class WebSocket(WebSocketClient, PortalSessionMixin):

    def print(self, text, styles=True, highlight=False) -> str:
        """
        A thin wrapper around Rich.Console's print. Returns the exported data.
        """
        self.console.print(text, highlight=highlight)
        html = self.console.export_html(clear=True, inline_styles=True)
        soup = BeautifulSoup(html, "html.parser")

        pre = soup.find("pre")
        if pre:
            return ''.join(map(str, pre.contents))

    def send_text(self, *args, **kwargs):
        """
        Send text data. This will pre-process the text for
        color-replacement, conversion to html etc.

        Args:
            text (str): Text to send.

        Keyword Args:
            options (dict): Options-dict with the following keys understood:
                - raw (bool): No parsing at all (leave ansi-to-html markers unparsed).
                - nocolor (bool): Clean out all color.
                - screenreader (bool): Use Screenreader mode.
                - send_prompt (bool): Send a prompt with parsed html

        """
        if args:
            args = list(args)
            text = args[0]
            if text is None:
                return
        else:
            return

        flags = self.protocol_flags

        options = kwargs.pop("options", {})
        raw = options.get("raw", flags.get("RAW", False))
        client_raw = options.get("client_raw", False)
        nocolor = options.get("nocolor", flags.get("NOCOLOR", False))
        screenreader = options.get("screenreader", flags.get("SCREENREADER", False))
        prompt = options.get("send_prompt", False)
        highlight = options.get("highlight", False)

        if screenreader:
            # screenreader mode cleans up output
            text = _RE_SCREENREADER_REGEX.sub("", text)
        cmd = "prompt" if prompt else "text"
        args[0] = self.print(text, highlight=highlight)

        # send to client on required form [cmdname, args, kwargs]
        self.sendLine(json.dumps([cmd, args, kwargs]))

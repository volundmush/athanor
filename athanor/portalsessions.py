from evennia.server.portal.telnet import TelnetProtocol
from evennia.server.portal.ssh import SshProtocol
from evennia.server.portal.webclient import WebSocketClient
from athanor.ansi import RavensGleaning


class BundleMixin:
    def send_results(self, *args, **kwargs):
        """
        A Bundle is a collection of normal send_whatevers.
        This is normally only useful for the webclient, as telnet and SSH has no concept
        of a singular message.
        """
        for outputfunc, outargs, outkwargs in args:
            if callable(method := getattr(self, f"send_{outputfunc}", None)):
                method(*outargs, **outkwargs)


class PortalSessionMixin:
    def at_portal_sync(self):
        pass

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


class PlainTelnet(BundleMixin, PortalSessionMixin, TelnetProtocol):
    pass


class SecureTelnet(PlainTelnet):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.protocol_key = "telnet/ssl"


class SSHProtocol(BundleMixin, PortalSessionMixin, SshProtocol):
    pass


class WebSocket(BundleMixin, PortalSessionMixin, WebSocketClient):
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

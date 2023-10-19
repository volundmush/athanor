from django.conf import settings
from evennia.server.portal.telnet import TelnetProtocol
from evennia.server.portal.ssh import SshProtocol
from evennia.server.portal.webclient import WebSocketClient
from evennia.utils.utils import lazy_property
from athanor.ansi import RavensGleaning

class PortalSessionMixin:

    def at_portal_sync(self):
        pass

    def send_rich(self, *args, **kwargs):
        """
        Send rich data as ANSI color. args[0] should already be
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


class PlainTelnet(PortalSessionMixin, TelnetProtocol):
    pass


class SecureTelnet(PlainTelnet):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.protocol_key = "telnet/ssl"


class SSHProtocol(PortalSessionMixin, SshProtocol):
    pass


class WebSocket(PortalSessionMixin, WebSocketClient):
    converter = RavensGleaning()

    def send_rich(self, *args, **kwargs):
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

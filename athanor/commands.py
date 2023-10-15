from django.conf import settings
from evennia.commands.default.muxcommand import MuxCommand, MuxAccountCommand
from athanor.utils import Request


class _AthanorCommandMixin:

    def request(self, **kwargs) -> Request:
        if hasattr(self.caller, "account"):
            user = self.caller.account
            character = self.caller
        elif hasattr(self.caller, "at_post_login"):
            user = self.caller
            character = None
        req_kwargs = {"user": user, "character": character}
        req_kwargs.update(kwargs)
        return Request(**req_kwargs)

    def request_message(self, request):
        if message := request.results.get("message", ""):
            self.msg(message)

    def client_width(self):
        """
        Get the client screenwidth for the session using this command.

        Returns:
            client width (int): The width (in characters) of the client window.

        """
        if self.account:
            return self.account.client_width()
        return super().client_width()

    def styled_table(self, *args, **kwargs):
        if self.account:
            return self.account.styled_table(*args, **kwargs)
        return super().styled_table(*args, **kwargs)

    def styled_header(self, *args, **kwargs):
        if self.account:
            return self.account.styled_header(*args, **kwargs)
        return super().styled_header(*args, **kwargs)

    def styled_footer(self, *args, **kwargs):
        if self.account:
            return self.account.styled_footer(*args, **kwargs)
        return super().styled_footer(*args, **kwargs)

    def styled_separator(self, *args, **kwargs):
        if self.account:
            return self.account.styled_separator(*args, **kwargs)
        return super().styled_separator(*args, **kwargs)

    def msg_lines(self, out: list):
        self.msg("\n".join([str(o) for o in out]))


class AthanorCommand(_AthanorCommandMixin, MuxCommand):
    """
    This is a base command for all Athanor commands.
    """
    pass


class AthanorAccountCommand(_AthanorCommandMixin, MuxAccountCommand):
    """
    This is a base command for all Athanor commands.
    """
    pass

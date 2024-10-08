"""
Implements Athanor-specific command infrastructure and helper utilities to make writing
commands a much easier and more streamlined task.
"""
import evennia
from evennia.utils.utils import inherits_from
from evennia.commands.default.muxcommand import MuxCommand, MuxAccountCommand
from athanor.utils import utcnow


class _AthanorCommandMixin:

    def at_post_cmd(self):
        """
        A hook that is called after the command is executed. This is used to flush the buffer.
        """
        self.record_idle_time()

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
        """
        A shorthand for sending a list of strings to the user.
        """
        self.msg("\n".join([str(o) for o in out]))

    def record_idle_time(self):
        playview = None
        if self.session:
            playview = self.session.playview
        if not playview:
            if inherits_from(self.caller, evennia.DefaultObject):
                playview = getattr(self.caller, "playview", None)
        if playview:
            playview.last_active = utcnow()


class AthanorCommand(_AthanorCommandMixin, MuxCommand):
    """
    This is a base command for all Athanor commands.
    """


class AthanorAccountCommand(_AthanorCommandMixin, MuxAccountCommand):
    """
    This is a base command for all Athanor commands.
    """

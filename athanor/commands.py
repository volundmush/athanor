from evennia.utils.utils import lazy_property
from evennia.commands.default.muxcommand import MuxCommand, MuxAccountCommand
from athanor.utils import Operation, ev_to_rich
from rich.table import Table
from rich.box import ASCII2
from rich.console import Group


class OutputBuffer:
    """
    This class manages output for aggregating Rich printables (it can also accept ANSIStrings and strings
    with Evennia's markup) and sending them to the user in a single message. It's used by the AthanorCommand
    as a major convenience.
    """

    def __init__(self, method):
        self.method = method.msg if hasattr(method, "msg") else method
        self.buffer = list()
        self.dict = dict()

    def append(self, obj):
        if isinstance(obj, str):
            self.buffer.append(ev_to_rich(obj))
        elif hasattr(obj, "__rich_console__"):
            self.buffer.append(obj)
        else:
            self.buffer.append(ev_to_rich(str(obj)))

    def __getitem__(self, key):
        return self.dict[key]

    def __setitem__(self, key, value):
        self.dict[key] = value

    def __delitem__(self, key):
        del self.dict[key]

    def reset(self):
        self.buffer.clear()
        self.dict.clear()

    def flush(self):
        if not self.buffer:
            return
        group = Group(*self.buffer) if len(self.buffer) > 1 else self.buffer[0]
        value = {"rich": (group, self.dict) if self.dict else group}
        self.method(**value)
        self.reset()


class _AthanorCommandMixin:
    def create_buffer(self, method=None):
        if not method:
            method = self.msg
        return OutputBuffer(method)

    @lazy_property
    def buffer(self):
        self._buffer_created = True
        return self.create_buffer()

    def at_post_cmd(self):
        if getattr(self, "_buffer_created", False):
            self.buffer.flush()

    def operation(self, **kwargs) -> Operation:
        user = None
        character = None
        if hasattr(self.caller, "account"):
            user = self.caller.account
            character = self.caller
        elif hasattr(self.caller, "at_post_login"):
            user = self.caller
            character = None
        req_kwargs = {"user": user}
        if character:
            req_kwargs["character"] = character
        req_kwargs.update(kwargs)
        return Operation(**req_kwargs)

    def op_message(self, operation):
        if message := operation.results.get("message", ""):
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

    def rich_table(self, *args, **kwargs) -> Table:
        """
        Creates and returns a ready-made Rich Table with the given arguments,
        pre-stylized. This is a fancy wrapper for convenience.
        """
        if self.account:
            return self.account.rich_table(*args, **kwargs)
        real_kwargs = {
            "box": ASCII2,
            "border_style": "magenta",
            "header_style": "bold",
            "title_style": "bold",
            "expand": True,
        }
        real_kwargs.update(kwargs)
        return Table(*args, **real_kwargs)

    def msg_lines(self, out: list):
        """
        A shorthand for sending a list of strings to the user.
        """
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

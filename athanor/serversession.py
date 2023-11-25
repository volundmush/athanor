from rich.color import ColorSystem
from django.conf import settings
import evennia
from evennia.server.serversession import ServerSession
from evennia.utils.utils import lazy_property
from rich.highlighter import ReprHighlighter
from rich.box import ASCII2
from rich.markdown import Markdown
from athanor.error import AthanorTraceback
from athanor.playviews import DefaultPlayview

_FUNCPARSER = None

_ObjectDB = None
_PlayTC = None
_Select = None


class AthanorServerSession(ServerSession):
    """
    ServerSession class which integrates the Rich Console into Evennia.
    """

    def __init__(self):
        super().__init__()
        self.text_callable = None
        self.playview = None
        self._puid = None

    @lazy_property
    def console(self):
        # from athanor.mudrich import MudConsole
        from rich.console import Console as MudConsole

        if "SCREENWIDTH" in self.protocol_flags:
            width = self.protocol_flags["SCREENWIDTH"][0]
        else:
            width = settings.CLIENT_DEFAULT_WIDTH
        return MudConsole(
            color_system=self.rich_color_system(), width=width, file=self, record=True
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
        if "SCREENWIDTH" in self.protocol_flags:
            check._width = self.protocol_flags["SCREENWIDTH"][0]
        else:
            check._width = settings.CLIENT_DEFAULT_WIDTH
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
        new_kwargs = {"highlight": False}
        new_kwargs.update(kwargs)
        self.console.print(*args, **new_kwargs)
        return self.console.export_text(clear=True, styles=True)

    def data_out(self, **kwargs):
        """
        A second check to ensure that all uses of "rich" are getting processed properly.
        """
        if "text" in kwargs:
            t = kwargs.get("text", None)
            if isinstance(t, (list, tuple)):
                text, options = t
                if options.get("type", None) == "py_output":
                    del kwargs["text"]
                    kwargs["rich"] = self.console.render_str(
                        text,
                        markup=False,
                        highlight=True,
                        highlighter=ReprHighlighter(),
                    )

        if md := kwargs.pop("markdown", None):
            kwargs["rich"] = Markdown(md)

        if kwargs.pop("traceback", False):
            tb = AthanorTraceback(show_locals=True)
            tb.box = ASCII2
            kwargs["rich"] = tb

        if r := kwargs.get("rich", None):
            options = None
            if isinstance(r, (list, tuple)):
                ri, options = r
            else:
                ri = r
            printed = self.print(ri)
            kwargs["rich"] = (printed, options) if options else printed
        super().data_out(**kwargs)

    def load_sync_data(self, sessdata):
        super().load_sync_data(sessdata)
        self.update_rich()

    def at_sync(self):
        """
        This is called whenever a session has been resynced with the
        portal.  At this point all relevant attributes have already
        been set and self.account been assigned (if applicable).

        Since this is often called after a server restart we need to
        set up the session as it was.

        """
        super().at_sync()
        if not self.logged_in:
            # assign the unloggedin-command set.
            self.cmdset_storage = settings.CMDSET_UNLOGGEDIN

        self.cmdset.update(init_mode=True)

        if self.puid:
            # Explicitly clearing this out, because we've bypassed it.
            pass

    @property
    def puid(self):
        return self._puid

    @puid.setter
    def puid(self, value):
        self._puid = value
        if value is not None:
            obj = evennia.ObjectDB.objects.get(id=value)
            playview = obj.playview
            self.playview = playview
            playview.rejoin_session(self)

    @property
    def puppet(self):
        if not self.playview:
            return None
        return self.playview.puppet

    @puppet.setter
    def puppet(self, value):
        pass

from rich.color import ColorSystem
from django.conf import settings
import evennia
from evennia.server.serversession import ServerSession
from evennia.utils.utils import lazy_property, is_iter
from evennia.utils.optionhandler import OptionHandler

import athanor
from athanor.typeclasses.mixin import AthanorMessage

_FUNCPARSER = None

_ObjectDB = None
_PlayTC = None
_Select = None


class AthanorServerSession(AthanorMessage, ServerSession):
    """
    ServerSession class which integrates the Rich Console into Evennia.
    """

    # Determines which order command sets begin to be assembled from.
    # Sessions are usually first.
    cmd_order = 0
    cmd_order_error = 50
    cmd_type = "session"

    def __init__(self):
        super().__init__()
        self.text_callable = None
        self.playview = None

    def get_command_objects(self) -> dict[str, "CommandObject"]:
        """
        Overrideable method which returns a dictionary of all the kinds of CommandObjects
        linked to this ServerSession.
        In all normal cases, that's the Session itself, and possibly an account and puppeted
         object.
        The cmdhandler uses this to determine available cmdsets when executing a command.
        Returns:
            dict[str, CommandObject]: The CommandObjects linked to this Object.
        """
        out = {"session": self}
        if self.account:
            out["account"] = self.account
        if self.puppet:
            out["object"] = self.puppet
        if self.playview:
            out["playview"] = self.playview
        return out

    def at_cmdset_get(self, **kwargs):
        """
        A dummy hook all objects with cmdsets need to have
        Called just before cmdsets on this object are requested by the
        command handler. If changes need to be done on the fly to the
        cmdset before passing them on to the cmdhandler, this is the
        place to do it. This is called also if the object currently
        have no cmdsets.

        Keyword Args:
            caller (obj): The object requesting the cmdsets.
            current (cmdset): The current merged cmdset.
            force_init (bool): If `True`, force a re-build of the cmdset. (seems unused)
            **kwargs: Arbitrary input for overloads.
        """
        pass

    def get_cmdsets(self, caller, current, **kwargs):
        """
        Called by the CommandHandler to get a list of cmdsets to merge.
        Args:
            caller (obj): The object requesting the cmdsets.
            current (cmdset): The current merged cmdset.
            **kwargs: Arbitrary input for overloads.
        Returns:
            tuple: A tuple of (current, cmdsets), which is probably self.cmdset.current and self.cmdset.cmdset_stack
        """
        return self.cmdset.current, list(self.cmdset.cmdset_stack)

    @lazy_property
    def session_options(self):
        return OptionHandler(
            self,
            options_dict=settings.OPTIONS_ACCOUNT_DEFAULT,
            save_kwargs={"category": "option"},
            load_kwargs={"category": "option"},
        )

    @property
    def options(self):
        if self.account:
            return self.account.options
        return self.session_options

    @lazy_property
    def renderers(self):
        return athanor.RENDERERS.get(
            settings.PROTOCOL_RENDER_FAMILY.get(self.protocol_key, "ansi"), dict()
        )

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

    def split(self, value):
        if isinstance(value, (tuple, list)) and len(value) == 2:
            return value
        return value, dict()

    def process_output_kwargs(self, **in_kwargs):
        kwargs = dict()
        renderers = self.renderers

        for k, v in in_kwargs.items():
            if callable(renderer := renderers.get(k, None)):
                data, options = self.split(v)
                key, out_data, out_options = renderer(self, data, options)
                kwargs[key] = (out_data, out_options)
            else:
                match k:
                    case "options":
                        kwargs[k] = v
                    case _:
                        data, options = self.split(v)
                        kwargs[k] = (data, options)

        return kwargs

    def data_out(self, **kwargs):
        """
        A second check to ensure that all uses of "rich" are getting processed properly.
        """
        if bundle := kwargs.get("results", None):
            bundle, kw = self.split(bundle)
            new_bundle = [self.process_output_kwargs(**op) for op in bundle]
            kwargs["results"] = (new_bundle, kw) if kw else new_bundle

        kwargs = self.process_output_kwargs(**kwargs)

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
        if self.playview:
            return self.playview.id.id
        return None

    @puid.setter
    def puid(self, value):
        if value is not None:
            obj = evennia.ObjectDB.objects.get(id=value)
            playview = obj.playview
            self.playview = playview
            playview.rejoin_session(self)
        else:
            self.playview = None

    @property
    def puppet(self):
        if not self.playview:
            return None
        return self.playview.puppet

    @puppet.setter
    def puppet(self, value):
        pass

    def msg(
        self,
        text=None,
        from_obj=None,
        session=None,
        options=None,
        source=None,
        **kwargs,
    ):
        kwargs["options"] = options
        if text is not None:
            kwargs["text"] = text
        kwargs = self._msg_helper_format(**kwargs)
        kwargs.pop("session", None)
        kwargs.pop("from_obj", None)
        self.data_out(**kwargs)

    def uses_screenreader(self, session=None):
        if session is None:
            session = self
        if self.account:
            return self.account.uses_screenreader(session=session)
        return self.options.get("screenreader")

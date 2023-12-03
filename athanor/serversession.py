from rich.color import ColorSystem
from django.conf import settings
import evennia
from evennia.server.serversession import ServerSession
from evennia.utils.utils import lazy_property, is_iter
from evennia.utils.optionhandler import OptionHandler

import athanor


_FUNCPARSER = None

_ObjectDB = None
_PlayTC = None
_Select = None


class AthanorServerSession(ServerSession):
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
    def render_type(self):
        return settings.PROTOCOL_RENDER_FAMILY.get(self.protocol_key, "ansi")

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

    def uses_screenreader(self, session=None):
        if session is None:
            session = self
        if self.account:
            return self.account.uses_screenreader(session=session)
        return self.options.get("screenreader")

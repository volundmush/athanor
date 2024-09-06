from django.conf import settings
import evennia
from evennia.server.serversession import ServerSession

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

import time
from evennia.typeclasses.models import TypeclassBase
from twisted.internet.defer import inlineCallbacks, returnValue
from twisted.internet import reactor, task
from athanor.plays.models import PlayDB
from evennia.objects.objects import ObjectSessionHandler, _SESSID_MAX
from evennia.utils.utils import lazy_property, class_from_module, make_iter, to_str

from evennia.commands.cmdsethandler import CmdSetHandler

_SESSIONS = None
_CMDHANDLER = None


class PlaySessionHandler(ObjectSessionHandler):

    def _recache(self):
        global _SESSIONS
        if not _SESSIONS:
            from evennia.server.sessionhandler import SESSIONS as _SESSIONS
        self._sessid_cache = list(dict.fromkeys(sess for sess in self.obj.db_sessid if sess in _SESSIONS))
        if len(self._sessid_cache) != len(self.obj.db_sessid):
            # cache is out of sync with sessionhandler! Only retain the ones in the handler.
            self.obj.db_sessid = self._sessid_cache
            self.obj.save(update_fields=["db_sessid"])

    def add(self, session):
        global _SESSIONS
        if not _SESSIONS:
            from evennia.server.sessionhandler import SESSIONS as _SESSIONS
        try:
            sessid = session.sessid
        except AttributeError:
            sessid = session

        sessid_cache = self._sessid_cache
        if sessid in _SESSIONS and sessid not in sessid_cache:
            if len(sessid_cache) >= _SESSID_MAX:
                return
            sessid_cache.append(sessid)
            self.obj.db_sessid = sessid_cache
            self.obj.save(update_fields=["db_sessid"])


class PromptHandler:

    def __init__(self, owner):
        self.owner = owner
        self.task = None

    def prepare(self):
        if self.task:
            self.task.cancel()
        self.task = task.deferLater(reactor, 0.1, self.print)
        self.task.addErrback(self.error)

    def print(self):
        if self.owner.puppet:
            self.owner.msg(prompt=f"\n{self.owner.puppet.prompt.render()}\n")

    def error(self, err):
        pass


class DefaultPlay(PlayDB, metaclass=TypeclassBase):
    cmd_objects_sort_priority = 75
    lockstring = "control:id({account_id}) or perm(Admin);delete:id({account_id}) or perm(Admin)"

    @classmethod
    def create(cls, account, character):
        if (found := cls.objects.filter(id=character).first()):
            raise RuntimeError("Cannot create more than one Play per Character!")
        new_play = cls(id=character, db_puppet=character, db_account=account)
        new_play.save()
        return new_play

    def at_first_save(self):
        self.basetype_setup()

    def basetype_setup(self):
        self.cmdset.add_default(settings.CMDSET_PLAY, persistent=True)

    @lazy_property
    def prompt(self):
        return PromptHandler(self)

    @lazy_property
    def cmdset(self):
        return CmdSetHandler(self, True)

    @lazy_property
    def sessions(self):
        return PlaySessionHandler(self)

    @property
    def is_superuser(self):
        """
        Check if user has an account, and if so, if it is a superuser.

        """
        return (
                self.db_account
                and self.db_account.is_superuser
                and not self.db_account.attributes.get("_quell")
        )

    @inlineCallbacks
    def get_extra_cmdsets(self, caller, current, cmdsets):
        """
        Called by the CmdHandler to retrieve extra cmdsets from this object.

        For DefaultPlay, there are none yet.
        """
        extra = yield list()
        returnValue(extra)

    def get_cmd_objects(self):
        return {"account": self.account,
                "puppet": self.puppet,
                "play": self}

    def execute_cmd(self, raw_string, session=None, **kwargs):
        # break circular import issues
        global _CMDHANDLER
        if not _CMDHANDLER:
            from django.conf import settings
            from evennia.utils.utils import class_from_module
            _CMDHANDLER = class_from_module(settings.COMMAND_HANDLER)

        # nick replacement - we require full-word matching.
        # do text encoding conversion
        raw_string = self.id.nicks.nickreplace(
            raw_string, categories=("inputline", "channel"), include_account=True
        )
        handler = _CMDHANDLER(session or self, raw_string, **kwargs)
        return handler.execute()

    def at_start(self):
        """
        Called when the Play object is created. This should prepare the character for play, display updates
        to the player, etc.
        """

    def msg(self, **kwargs):
        for session in self.sessions.all():
            session.data_out(**kwargs)

    @property
    def idle_time(self):
        """
        Returns the idle time of the least idle session in seconds. If
        no sessions are connected it returns nothing.

        """
        idle = [session.cmd_last_visible for session in self.sessions.all()]
        if idle:
            return time.time() - float(max(idle))
        return None

    @property
    def connection_time(self):
        """
        Returns the maximum connection time of all connected sessions
        in seconds. Returns nothing if there are no sessions.

        """
        conn = [session.conn_time for session in self.sessions.all()]
        if conn:
            return time.time() - float(min(conn))
        return None

    def on_additional_session(self, session):
        pass

    def on_first_session(self, session):
        pass
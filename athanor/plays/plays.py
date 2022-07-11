import time
from django.conf import settings
from evennia.typeclasses.models import TypeclassBase
from twisted.internet.defer import inlineCallbacks, returnValue
from twisted.internet import reactor, task
from athanor.plays.models import PlayDB
from evennia.objects.objects import ObjectSessionHandler, _SESSID_MAX
from evennia.utils.utils import lazy_property, class_from_module, make_iter, to_str, logger

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

    def __repr__(self):
        return f"<{self.__class__.__name__}: {repr(self.id)}>"

    @classmethod
    def create(cls, account, character):
        if (found := cls.objects.filter(id=character).first()):
            raise RuntimeError("Cannot create more than one Play per Character!")
        new_play = cls(id=character, db_puppet=character, db_account=account)
        new_play.save()
        character.account = account
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
        self.deploy_character()

    def msg(self, text=None, session=None, **kwargs):
        if text:
            kwargs["text"] = text
            self.prompt.prepare()
        if session:
            session.data_out(**kwargs)
        else:
            for sess in self.sessions.all():
                sess.data_out(**kwargs)

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

    def deploy_character(self):
        c = self.id
        if c.location is not None:
            return

        if (found := c.db.prelogout_location):
            place_in = found
        elif (found := c.home):
            place_in = found
        else:
            place_in = settings.SAFE_FALLBACK

        if not c.move_to(place_in, quiet=True, move_hooks=False):
            self.msg("Cannot find a safe place to put you. Contact staff!")
            logger.error(f"Cannot deploy_character() for {c}, No Acceptable locations.")
            return
        c.location.at_object_receive(c, None)

        c.location.msg_contents(text="$You() has entered the game.", exclude=c, from_obj=c)


    def possess(self, obj, msg=None):
        if msg is None:
            msg = f"You become {obj.get_display_name(looker=self.id)}"
        self.puppet = obj
        self.msg(msg)
        self.puppet.at_possess(self)

    def is_possessing(self):
        return self.id != self.db_puppet

    def unposess(self):
        puppet = self.puppet
        self.msg(text=f"You stop possessing {puppet.get_display_name(looker=self.id)} and return to being {self.id.get_display_name(looker=self.id)}")
        self.puppet = self.id
        puppet.at_unpossess(self)

    def cleanup_misc(self):
        if self.is_possessing():
            self.unposess()

    def extract_character(self):
        if self.id.location:
            location = self.id.location
            location.msg_contents(text="$You() $conj(leaves) the game.", from_obj=self.id)
            location.at_object_leave(self.id, None)
            self.id.db.prelogout_location = location
            self.id.location = None

    def update_stats(self):
        pass

    def terminate_play(self):
        self.cleanup_misc()
        self.extract_character()
        self.update_stats()
        if (sessions := self.sessions.all()):
            for sess in sessions:
                sess.unbind_play()
        self.delete()

    def at_server_cold_stop(self):
        """
        If this is a cold stop, then all Plays must be force-terminated.
        """
        self.terminate_play()

    def at_server_cold_start(self):
        """
        There technically should be no Plays in existence on a cold start.
        But, if the game crashes or so on, they could remain in the database.
        If so, this method will clean them up.
        """
        self.terminate_play()

    def at_cmdset_get(self):
        pass
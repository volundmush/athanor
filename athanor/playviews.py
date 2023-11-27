from .models import PlayviewDB
from .managers import PlayviewManager

from django.conf import settings
from django.utils.translation import gettext as _
from evennia.commands.cmdsethandler import CmdSetHandler
from evennia.typeclasses.models import TypeclassBase
from evennia.utils.utils import lazy_property, make_iter, logger, to_str
from evennia.utils.optionhandler import OptionHandler
from evennia.objects.objects import ObjectSessionHandler
from evennia.server import signals
import athanor
from athanor.typeclasses.mixin import AthanorAccess
from athanor.utils import utcnow


class DefaultPlayview(AthanorAccess, PlayviewDB, metaclass=TypeclassBase):
    system_name = PlayviewManager.system_name
    objects = PlayviewManager()

    # Determines which order command sets begin to be assembled from.
    # Playviews are usually third.
    cmd_order = 75
    cmd_order_error = 75
    cmd_type = "playview"

    def __str__(self):
        return f"{self.id} (playview)"

    def __repr__(self):
        return f"<{self.__class__.__name__}: {self.id} (playview)>"

    @lazy_property
    def cmdset(self):
        return CmdSetHandler(self, True)

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
        return {"playview": self, "account": self.account, "object": self.puppet}

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

    def __bool__(self):
        try:
            return bool(self.id)
        except Exception:
            return False

    @property
    def _content_types(self):
        return self.id._content_types

    @lazy_property
    def sessions(self):
        return ObjectSessionHandler(self)

    def at_first_save(self):
        pass

    def basetype_setup(self):
        self.cmdset.add_default(settings.CMDSET_PLAYVIEW, persistent=True)

    def add_session(self, session, **kwargs):
        session.playview = self
        if self.sessions.count() == 0:
            self.at_init_playview(session, **kwargs)
        # do the connection
        self.sessions.add(session)
        self.id.account = self.account
        if self.sessions.count() == 1:
            self.at_start_playview(session, **kwargs)
        self.at_add_session(session, **kwargs)
        self.execute_look(**kwargs)

    def at_add_session(self, session, **kwargs):
        pass

    def rejoin_session(self, session, **kwargs):
        self.sessions.add(session)
        self.id.account = self.account

    def at_init_playview(self, session, **kwargs):
        self.id.at_pre_puppet(self, session=session)
        # used to track in case of crash so we can clean up later
        self.id.tags.add("puppeted", category="account")
        self.id.locks.cache_lock_bypass(self.id)
        self.id.at_post_puppet()
        signals.SIGNAL_OBJECT_POST_PUPPET.send(
            sender=self.id, account=self, session=session
        )

    def at_start_playview(self, session, **kwargs):
        self.at_login(**kwargs)

    def at_login(self, **kwargs):
        self.record_login()
        self.unstow()
        self.announce_join_game()

    def unstow(self, **kwargs):
        if self.location is None:
            # Make sure character's location is never None before being puppeted.
            # Return to last location (or home, which should always exist)
            if settings.OFFLINE_CHARACTERS_VOID_STORAGE:
                location = (
                    self.db.prelogout_location
                    if self.db.prelogout_location
                    else self.id.home
                )
            else:
                location = self.id.home

            if location:
                self.id.location = location
                self.location.at_object_receive(self.id, None)

        if self.location:
            self.db.prelogout_location = (
                self.location
            )  # save location again to be sure.
        else:
            self.account.msg(
                _("|r{obj} has no location and no home is set.|n").format(obj=self.id)
            )

    def record_login(self, current_time=None, **kwargs):
        if current_time is None:
            current_time = utcnow()
        p = self.id.playtime
        p.last_login = current_time
        p.save(update_fields=["last_login"])

        ca = p.per_account.get_or_create(account=self.account)[0]
        ca.last_login = current_time
        ca.save(update_fields=["last_login"])

    def announce_join_game(self):
        """
        Announces to the room that a character has entered the game. Overload this to change the message.
        """
        # this should ALWAYS be true, but in case something weird's going on...
        if self.id.location:
            self.id.location.msg_contents(
                settings.ACTION_TEMPLATES.get("login"),
                exclude=[self.id],
                from_obj=self.id,
            )

    @classmethod
    def create(cls, account, character):
        obj = cls.objects.create(
            id=character, account=account, db_puppet=character, db_key=character.key
        )
        obj.save()
        return obj

    def execute_look(self, **kwargs):
        self.msg(f"\nYou become |c{self.get_display_name(self)}|n.\n")
        if self.location:
            self.msg((self.id.at_look(self.location), {"type": "look"}), options=None)
        else:
            self.msg("You are nowhere. That's not good. Contact an admin.")

    @property
    def location(self):
        return self.id.location

    @property
    def db(self):
        return self.id.db

    @property
    def msg(self):
        return self.id.msg

    def uses_screenreader(self, session=None):
        if not self.account:
            return False
        return self.account.uses_screenreader(session=session)

    def at_logout(self, **kwargs):
        """
        A simple, easily overloaded hook called when a character leaves the game.
        """
        self.announce_leave_game()
        self.cleanup()

    def announce_leave_game(self):
        # this should ALWAYS be true, but in case something weird's going on...
        if self.id.location:
            self.id.location.msg_contents(
                settings.ACTION_TEMPLATES.get("logout"),
                exclude=[self.id],
                from_obj=self.id,
            )

    def record_logout(self, current_time=None, **kwargs):
        if current_time is None:
            current_time = utcnow()
        p = self.id.playtime
        p.last_logout = current_time
        p.save(update_fields=["last_logout"])

        ca = p.per_account.get_or_create(account=self.account)[0]
        ca.last_logout = current_time
        ca.save(update_fields=["last_logout"])

    def stow(self, **kwargs):
        if not settings.OFFLINE_CHARACTERS_VOID_STORAGE:
            return

        # this should ALWAYS be true, but in case something weird's going on...
        if not self.id.location:
            return

        self.id.db.prelogout_location = self.id.location
        self.id.location.at_object_leave(self.id, None, stowed=True)
        self.id.location = None

    def at_cold_start(self, **kwargs):
        """
        Called by Athanor when the game starts up cold. This needs to clean up the playview.
        """
        self.cleanup(current_time=None, **kwargs)

    def at_cold_stop(self, **kwargs):
        self.cleanup(current_time=None, **kwargs)

    def cleanup(self, current_time=None, **kwargs):
        self.stow(**kwargs)

        for sess in self.sessions.all():
            self.remove_session(sess, logout_type="cleanup", **kwargs)

        self.record_logout(current_time=current_time, **kwargs)
        self.id.tags.remove("puppeted", category="account")
        self.delete()

    def remove_session(self, session, logout_type="disconnect", **kwargs):
        self.sessions.remove(session)
        session.playview = None
        signals.SIGNAL_OBJECT_POST_UNPUPPET.send(
            sender=self.id, session=session, account=self.account
        )
        if logout_type == "disconnect":
            self.at_disconnect(session=session, **kwargs)
            if self.sessions.count() == 0:
                self.at_no_sessions(logout_type=logout_type, **kwargs)

    def at_disconnect(self, session, **kwargs):
        """
        Called when a session is disconnected unexpectedly.
        """
        self.announce_linkdead()

    def announce_linkdead(self):
        if self.sessions.count() == 0:
            if self.id.location:
                self.id.location.msg_contents(
                    settings.ACTION_TEMPLATES.get("linkdead"),
                    exclude=[self.id],
                    from_obj=self.id,
                )
        else:
            if self.id.location:
                self.id.location.msg_contents(
                    settings.ACTION_TEMPLATES.get("linklost"),
                    from_obj=self.id,
                )
            else:
                self.msg("|rYou lost a link.|n")

    def at_no_sessions(self, logout_type="disconnect", **kwargs):
        """
        Called when the last session is disconnected UNEXPECTEDLY.
        """
        self.at_logout(logout_type=logout_type, **kwargs)

    def can_quit(self, **kwargs):
        return True

    def do_quit(self, **kwargs):
        if not self.can_quit(**kwargs):
            return
        account = self.account
        sessions = self.sessions.all()
        self.id.msg("You quit the game.")
        self.account.db._last_puppet = self.id
        self.at_logout(**kwargs)
        if settings.AUTO_PUPPET_ON_LOGIN:
            for session in sessions:
                self.account.disconnect_session_from_account(session, "quit")
        else:
            for session in sessions:
                session.msg(account.at_look(target=[], session=session))

    def do_remove_session(self, session, logout_type="ooc", **kwargs):
        self.remove_session(session, logout_type=logout_type, **kwargs)
        session.msg(self.account.at_look(target=[], session=session))

from .models import PlayviewDB
from .managers import PlayviewManager

from django.conf import settings
from django.utils.translation import gettext as _
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

    def msg(
        self,
        text=None,
        from_obj=None,
        session=None,
        options=None,
        source=None,
        **kwargs,
    ):
        """
        Emits something to a session attached to the object.

        Args:
            text (str or tuple, optional): The message to send. This
                is treated internally like any send-command, so its
                value can be a tuple if sending multiple arguments to
                the `text` oob command.
            from_obj (obj or list, optional): object that is sending. If
                given, at_msg_send will be called. This value will be
                passed on to the protocol. If iterable, will execute hook
                on all entities in it.
            session (Session or list, optional): Session or list of
                Sessions to relay data to, if any. If set, will force send
                to these sessions. If unset, who receives the message
                depends on the MULTISESSION_MODE.
            options (dict, optional): Message-specific option-value
                pairs. These will be applied at the protocol level.
            source (obj, optional): Source object of the message. This is the object
                relaying text. It's likely self.id or self.puppet
        Keyword Args:
            any (string or tuples): All kwarg keys not listed above
                will be treated as send-command names and their arguments
                (which can be a string or a tuple).

        Notes:
            `at_msg_receive`and at_post_msg_receive will be called on this Object.
            All extra kwargs will be passed on to the protocol.

        """
        kwargs["options"] = options
        self._msg_helper_text_format(text, kwargs)

        # try send hooks
        self._msg_helper_from_obj(from_obj=from_obj, **kwargs)

        if not self._msg_helper_receive(from_obj=from_obj, **kwargs):
            return

        # relay to session(s)
        self._msg_helper_session_relay(session=session, **kwargs)

        self.at_post_msg_receive(from_obj=from_obj, **kwargs)

    def at_post_msg_receive(self, from_obj=None, **kwargs):
        """
        Overloadable hook which receives the kwargs that exist at the tail end of self.msg()'s processing.

        This might be used for logging and similar purposes.

        Kwargs:
            from_obj (DefaultObject or list[DefaultObject]): The objects that sent the message.
            **kwargs: The kwargs from the end of message, using the Evennia outputfunc format.
        """
        for t in self._content_types:
            athanor.EVENTS[f"{t}_at_post_msg_receive"].send(
                sender=self, from_obj=from_obj, **kwargs
            )

    def _msg_helper_session_relay(self, session=None, **kwargs):
        """
        Helper method for object.msg() to send output to sessions.

        Kwargs:
            session (Session or list[Session], optional): Sessions to specifically send the message to, if any.
            **kwargs: The message being sent, as evennia outputfuncs. this will be passed directly to session.data_out()
        """
        sessions = make_iter(session) if session else self.sessions.all()
        for session in sessions:
            session.data_out(**kwargs)

    def _msg_helper_text_format(self, text, kwargs: dict):
        """
        Helper method that formats the text kwarg for sending.

        Args:
            text (str or None): A string object or something that can be coerced into a string.
            kwargs: The outputfuncs dictionary being built up for this .msg() operation.
        """
        if text is not None:
            if isinstance(text, (tuple, list)):
                split_text, kw = text
                if hasattr(split_text, "__rich_console__"):
                    kwargs["rich"] = (split_text, kw)
                    text = None
                else:
                    kwargs["text"] = text
            elif hasattr(text, "__rich_console__"):
                kwargs["rich"] = text
                text = None

        if text is not None:
            if not (isinstance(text, str) or isinstance(text, tuple)):
                # sanitize text before sending across the wire
                try:
                    text = to_str(text)
                except Exception:
                    text = repr(text)
            kwargs["text"] = text

    def _msg_helper_from_obj(self, from_obj=None, **kwargs):
        """
        Helper method for .msg() that handles calling at_msg_send on the from_obj.

        Kwargs:
            text (str or None): A string object or something that can be coerced into a string.
            from_obj (DefaultObject or list[DefaultObject]): The objects to call the hook on.
            **kwargs: The outputfuncs being sent by this .msg() call.
        """
        if from_obj:
            for obj in make_iter(from_obj):
                try:
                    obj.at_msg_send(
                        text=kwargs.pop("text", None), to_obj=self, **kwargs
                    )
                except Exception:
                    logger.log_trace()

    def _msg_helper_receive(self, from_obj=None, **kwargs) -> bool:
        """
        Helper method for .msg() that handles calling at_msg_receive on this object.

        Kwargs:
            text (str or None): A string object or something that can be coerced into a string.
            from_obj (DefaultObject or list[DefaultObject]): The objects to call the hook on.
            **kwargs: The outputfuncs being sent by this .msg() call.

        Returns:
            result (bool): True if the message should be sent, False if it should be aborted.
        """
        try:
            if not self.at_msg_receive(
                text=kwargs.pop("text", None), from_obj=from_obj, **kwargs
            ):
                # if at_msg_receive returns false, we abort message to this object
                return False
        except Exception:
            logger.log_trace()
        return True

    def uses_screenreader(self, session=None):
        if not self.account:
            return False
        return self.account.uses_screenreader(session=session)

    def at_msg_receive(self, text=None, from_obj=None, **kwargs):
        return True

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

import typing
from django.conf import settings
from evennia.objects.objects import DefaultCharacter, DefaultObject
import athanor
from athanor.utils import utcnow
from .mixin import AthanorObject


class AthanorCharacter(AthanorObject, DefaultCharacter):
    """
    Abstract base class for Athanor characters.
    Do not instantiate directly.
    """

    lock_default_funcs = athanor.OBJECT_CHARACTER_DEFAULT_LOCKS
    _content_types = ("character",)
    lockstring = ""

    def is_player(self):
        """
        The default Athanor assumption is that all AthanorCharacters are player characters.
        If this is not the case, put logic here to answer the question.
        """
        return True

    def basetype_setup(self):
        """
        Avoids calling super() in order to avoid setting unnecessary locks.
        """
        # add the default cmdset
        self.cmdset.add_default(settings.CMDSET_CHARACTER, persistent=True)

    def access_check_puppet(self, accessing_obj, **kwargs):
        """
        All characters can be puppeted by the Account they are assigned to,
        as a basic assumption.
        """
        if not self.is_player():
            return False
        if not (ao := getattr(self, "account_owner", None)):
            return False
        return ao.account == accessing_obj

    def at_post_puppet(self, **kwargs):
        """
        Called just after puppeting has been completed and all
        Account<->Object links have been established.

        Overloads the default Evennia method. This variant is sensitive
        to existing sessions and sets basic Athanor properties related
        to play time tracking.

        For custom game logic, it is recommended to overload at_login()
        instead of this method.
        """
        if self.sessions.count() == 1:
            self.at_login()
        else:
            self.msg(f"\nYou become |c{self.get_display_name(self)}|n.\n")

        if self.location:
            self.msg((self.at_look(self.location), {"type": "look"}), options=None)
        else:
            self.msg("You are nowhere. That's not good. Contact an admin.")

    def at_login(self):
        """
        A simple, easily overloaded hook called when a character first joins the game.
        """
        if self.is_player():
            now = utcnow()
            p = self.playtime
            p.last_login = now
            p.save(update_fields=["last_login"])

            ca = p.per_account.get_or_create(account=self.account)[0]
            ca.last_login = now
            ca.save(update_fields=["last_login"])

        self.announce_join_game()

    def announce_join_game(self):
        """
        Announces to the room that a character has entered the game. Overload this to change the message.
        """
        # this should ALWAYS be true, but in case something weird's going on...
        if self.location:
            self.location.msg_contents(
                settings.ACTION_TEMPLATES.get("login"), exclude=[self], from_obj=self
            )

    def at_pre_unpuppet(self):
        if self.sessions.count() == 1:
            self.at_pre_logout()

    def at_post_unpuppet(self, account=None, session=None, **kwargs):
        super().at_post_unpuppet(account=account, session=session, **kwargs)
        if not self.sessions.count() or kwargs.get("shutdown", False):
            self.at_logout()

    def at_pre_logout(self):
        """
        This is called just before the last session disconnects, while self.account
        is still valid.
        """
        if self.is_player():
            now = utcnow()
            p = self.playtime
            p.last_logout = now
            p.save(update_fields=["last_logout"])

            ca = p.per_account.get_or_create(account=self.account)[0]
            ca.last_logout = now
            ca.save(update_fields=["last_logout"])

    def at_logout(self):
        """
        A simple, easily overloaded hook called when a character leaves the game.
        """
        self.announce_leave_game()
        self.stow()

    def announce_leave_game(self):
        # this should ALWAYS be true, but in case something weird's going on...
        if self.location:
            self.location.msg_contents(
                settings.ACTION_TEMPLATES.get("logout"), exclude=[self], from_obj=self
            )

    def stow(self):
        if not self.is_player():
            return

        if not settings.OFFLINE_CHARACTERS_VOID_STORAGE:
            return

        # this should ALWAYS be true, but in case something weird's going on...
        if not self.location:
            return

        self.db.prelogout_location = self.location
        self.location.at_object_leave(self, None, stowed=True)
        self.location = None

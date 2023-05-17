import typing
from .mixin import AthanorBase
from django.conf import settings
from evennia.objects.objects import DefaultCharacter, DefaultObject
from athanor import CHARACTERS_ONLINE
from athanor.utils import utcnow


class _AthanorCharacter(DefaultCharacter, AthanorBase):
    """
    Abstract base class for Athanor characters.
    Do not instantiate directly.
    """
    _content_types = ("character",)

    def at_pre_move(self, destination: typing.Optional[DefaultObject], **kwargs):
        """
        Called just before moving object to destination.
        If returns False, move is cancelled.
        """
        if not destination:
            return True

        # Characters may only exist inside Rooms, Sectors, or Grids.
        return any(ctype in destination._content_types for ctype in ("room", "grid", "sector"))

    def at_object_receive(self, obj: DefaultObject, source_location: typing.Optional[DefaultObject], move_type="move", **kwargs):
        """
        Called after an object has been moved into this object.

        Anything inside a character is an item, in their inventory or equipped.

        It's assumed that coordinate 0 is the character's inventory, and coordinates 1+ are their equipment slots.
        """
        obj.db.coordinates = 0


class AthanorPlayerCharacter(_AthanorCharacter):
    """
    This is the base for all Player Characters.

    Note that Athanor only supports PCs as direct Puppets. Use the 'possess' framework
    to allow PCs to control NPCs or other entities.
    """
    is_player = True

    def at_object_creation(self):
        super().at_object_creation()
        self.db.total_playtime = 0
        self.db.is_online = False
        self.db.last_login = None
        self.db.last_logout = None
        self.db.last_activity = None
        self.db.last_online = None

    def calculate_playtime(self):
        """
        Calculates total playtime in seconds.
        """
        tdelta = utcnow() - self.db.last_login
        return self.db.total_playtime + int(tdelta.total_seconds())

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
        if not self.db.is_online:
            self.db.is_online = True
            # Add to the CHARACTERS_ONLINE set for easy indexing of who list and
            # activity tracking.
            CHARACTERS_ONLINE.add(self)
            n = utcnow()
            self.db.last_login = n
            self.db.last_activity = n
            self.db.last_online = n
            self.at_login()
        else:
            self.msg(f"\nYou become |c{self.get_display_name(self)}|n.\n")

    def at_login(self):
        """
        A simple, easily overloaded hook called when a character first joins the game.
        """
        self.announce_join_game()

    def announce_join_game(self):
        """
        Announces to the room that a character has entered the game. Overload this to change the message.
        """
        # this should ALWAYS be true, but in case something weird's going on...
        if self.location:
            self.location.msg_contents(settings.ACTION_TEMPLATES.get("login"), exclude=[self], from_obj=self)
        else:
            self.msg(f"\nYou become |c{self.get_display_name(self)}|n. Where are you, though?\n")

    def at_post_unpuppet(self, account=None, session=None, **kwargs):
        if not self.sessions.count() or kwargs.get("shutdown", False):
            self.db.is_online = False
            CHARACTERS_ONLINE.remove(self)
            # Pulls from kwargs in case this is called by at_server_cold_boot
            self.db.last_logout = kwargs.get("last_logout", utcnow())
            tdelta = self.db.last_logout - self.db.last_login
            self.db.total_playtime = self.db.total_playtime + int(tdelta.total_seconds())
            self.at_logout()

    def at_logout(self):
        """
        A simple, easily overloaded hook called when a character leaves the game.
        """
        self.announce_leave_game()
        self.stow()

    def announce_leave_game(self):
        # this should ALWAYS be true, but in case something weird's going on...
        if self.location:
            self.location.msg_contents(settings.ACTION_TEMPLATES.get("logout"), exclude=[self], from_obj=self)

    def stow(self):
        # this should ALWAYS be true, but in case something weird's going on...
        if self.location:
            self.db.prelogout_location = self.location
            self.location.at_object_leave(self, None)
            self.location = None

    def get_anonymous_name(self, looker=None, **kwargs):
        """
        Each game will have their own way of handling this, so this is a hook for that.
        """
        return self.key

    def get_display_name(self, looker=None, **kwargs) -> str:
        """
        Returns the display name of the object as seen by looker.
        """
        if not looker:
            return self.key
        if self.locks.check_lockstring(looker, "perm(Builder)"):
            return f"{self.key}(#{self.id})"
        if settings.DUB_SYSTEM_ENABLED:
            if hasattr(looker, "get_dub_name") and (dub_name := looker.get_dub_name(self)):
                return dub_name
            else:
                return self.get_anonymous_name(looker=looker, **kwargs)
        else:
            return self.key

    def get_anonymous_keywords(self, looker, **kwargs) -> typing.Set[str]:
        """
        Each game will have their own way of handling this, so this is a hook for that.
        """
        results = set()
        for word in self.key.split():
            results.add(word.lower())
        return results

    def generate_keywords(self, looker, **kwargs) -> typing.Set[str]:
        results = set()
        for alias in self.aliases.all():
            for word in alias.split():
                results.add(word.lower())
        if self.locks.check_lockstring(looker, "perm(Builder)"):
            for word in self.key.split():
                results.add(word.lower())
        elif settings.DUB_SYSTEM_ENABLED:
            if hasattr(looker, "get_dub_name"):
                if (dub_name := looker.get_dub_name(self)):
                    for word in dub_name.split():
                        results.add(word.lower())
                else:
                    results += self.get_anonymous_keywords(looker, **kwargs)
            else:
                for word in self.key.split():
                    results.add(word.lower())
        else:
            for word in self.key.split():
                results.add(word.lower())
        return results


class AthanorNonPlayerCharacter(_AthanorCharacter):
    """
    The base for all non-player characters.
    """
    is_player = False
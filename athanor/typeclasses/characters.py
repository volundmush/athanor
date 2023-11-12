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

    def access_check_puppet(self, accessing_obj, **kwargs):
        """
        All characters can be puppeted by the Account they are assigned to,
        as a basic assumption.
        """
        if not (
            account := self.attributes.get("account", category="system", default=None)
        ):
            return False
        return account == accessing_obj

    def basetype_setup(self):
        """
        Avoids calling super() in order to avoid setting unnecessary locks.
        """
        # add the default cmdset
        self.cmdset.add_default(settings.CMDSET_CHARACTER, persistent=True)

    def at_pre_move(self, destination: typing.Optional[DefaultObject], **kwargs):
        """
        Called just before moving object to destination.
        If returns False, move is cancelled.
        """
        if not destination:
            return True

        # Characters may only exist inside Rooms, Sectors, or Grids.
        return any(
            ctype in destination._content_types for ctype in ("room", "grid", "sector")
        )

    def at_object_receive(
        self,
        obj: DefaultObject,
        source_location: typing.Optional[DefaultObject],
        move_type="move",
        **kwargs,
    ):
        """
        Called after an object has been moved into this object.

        Anything inside a character is an item, in their inventory or equipped.

        It's assumed that coordinate 0 is the character's inventory, and coordinates 1+ are their equipment slots.
        """
        obj.db.coordinates = 0


class AthanorPlayerCharacter(AthanorCharacter):
    """
    This is the base for all Player Characters.

    Note that Athanor only supports PCs as direct Puppets. Use the 'possess' framework
    to allow PCs to control NPCs or other entities.
    """

    is_player = True

    _content_types = ("character", "player")

    def at_object_creation(self):
        super().at_object_creation()
        self.db.total_playtime = 0
        self.db.last_login = None
        self.db.last_logout = None
        self.db.last_activity = None
        self.db.last_online = None

    def calculate_playtime(self):
        """
        Calculates total playtime in seconds.
        """
        if not self.db.last_login:
            return 0
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
        if self.sessions.count() == 1:
            # Add to the CHARACTERS_ONLINE set for easy indexing of who list and
            # activity tracking.
            athanor.CHARACTERS_ONLINE.add(self)
            n = utcnow()
            self.db.last_login = n
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
            self.location.msg_contents(
                settings.ACTION_TEMPLATES.get("login"), exclude=[self], from_obj=self
            )
        else:
            self.msg(
                f"\nYou become |c{self.get_display_name(self)}|n. Where are you, though?\n"
            )

    def at_post_unpuppet(self, account=None, session=None, **kwargs):
        if not self.sessions.count() or kwargs.get("shutdown", False):
            # Pulls from kwargs in case this is called by at_server_cold_boot
            self.db.last_logout = kwargs.get("last_logout", utcnow())
            tdelta = self.db.last_logout - self.db.last_login
            self.db.total_playtime = self.db.total_playtime + int(
                tdelta.total_seconds()
            )
            self.at_logout()

    def at_logout(self):
        """
        A simple, easily overloaded hook called when a character leaves the game.
        """
        self.announce_leave_game()
        self.stow()
        athanor.CHARACTERS_ONLINE.remove(self)

    def announce_leave_game(self):
        # this should ALWAYS be true, but in case something weird's going on...
        if self.location:
            self.location.msg_contents(
                settings.ACTION_TEMPLATES.get("logout"), exclude=[self], from_obj=self
            )

    def stow(self):
        if not settings.OFFLINE_CHARACTERS_VOID_STORAGE:
            return

        # this should ALWAYS be true, but in case something weird's going on...
        if not self.location:
            return

        self.db.prelogout_location = self.location
        self.location.at_object_leave(self, None, stowed=True)
        self.location = None

from evennia.objects.objects import DefaultObject, DefaultCharacter, DefaultRoom, DefaultExit
import typing
from collections import defaultdict
from django.conf import settings
from typing import Optional, List
from evennia.utils import logger, make_iter, to_str
from evennia.utils.ansi import strip_ansi, ANSIString
from evennia.utils.utils import lazy_property
from athanor.utils import utcnow, SafeDict
from athanor import CHARACTERS_ONLINE
from athanor.mudrich import STRIPPER
from evennia.objects.objects import _MSG_CONTENTS_PARSER
from athanor.equip import EquipHandler

class AthanorBase:
    """
    Mixin for general Athanor functionality.
    """

    # This field should contain string names of properties on this object
    # which provide an .all() method that returns an iterable of Modifiers.
    # Order according to preference.
    modifier_attrs: List[str] = []

    @lazy_property
    def equip(self):
        return EquipHandler(self)

    def get_type_family(self) -> str:
        """
        Returns the type of the location this object is in.
        """
        return self._content_types[0]

    def get_location_type_family(self) -> Optional[str]:
        """
        Convenience method for getting the type of the location this object is in.
        """
        if self.location:
            return self.location.get_type_family()

    def get_all_modifier_attrs(self):
        """
        A Generator that will iterate over all ModifierHandler attributes on this object.
        """
        return (getattr(self, attr) for attr in self.modifier_attrs if hasattr(self, attr))

    def get_all_modifiers(self, mod_tag: Optional[str] = None):
        """
        A Generator that will iterate over all Modifiers affecting this object.
        """
        return (
            modifier
            for attr in self.get_all_modifier_attrs()
            for modifier in attr.all(mod_tag=mod_tag)
        )

    def can_hear(self, target):
        return True

    def can_see(self, target):
        return True

    def can_detect(self, target):
        return self.can_see(target) or self.can_hear(target)

    def at_hear(self, text, from_obj, msg_type, extra, **kwargs):
        text = strip_ansi(text)
        first_quote = text.find('"')
        speech = text[first_quote + 1:-1]
        pass # self.dgscripts.trigger_speech(speech, from_obj, **kwargs)

    def at_see(self, text, from_obj, msg_type, extra, **kwargs):
        pass # self.dgscripts.trigger_act(strip_ansi(text), from_obj, **kwargs)

    def at_hear_speech(self, speech: str, speaker, msg_type: str, **kwargs):
        """
        A hook called by do_say and do_whisper which is used to make this object potentially react
        to words it hears. This could be useful for items that need magic words to activate, objects
        voice-controlled vehicles, or NPCs that react to speech.

        Args:
            speech (str): The text of the speech.
            speaker: The object that spoke.
            msg_type (str): The type of speech. "whisper" or "say" are the defaults.
            **kwargs: Additional arguments.
        """
        pass

    def check_delivery(self, from_obj, template: str, delivery: dict, mapping: dict):
        """
        Returns True if this object can deliver the message in the template to the target via the delivery method.
        """
        return True

    def do_action(self, template: str, delivery: dict, mapping: dict, targets: list, **kwargs):
        """
        Distribute a format-message as self to targets.
        """
        for target in targets:
            if target.check_delivery(self, template, delivery, mapping):
                target.send(template, extra_dict=delivery, mapping=mapping, from_obj=self, **kwargs)

    def _do_basic(self, mode: str, text: str, delivery: dict, **kwargs):
        if not self.location:
            self.msg("You can't do that here... you are nowhere.")
            return
        message = settings.ACTION_TEMPLATES.get(mode)
        text_clean = ANSIString(text).clean()
        mapping = {"text": text, "text_clean": text_clean, "here": self.location}
        self.do_action(message, delivery=delivery, mapping=mapping, targets=self.location.contents, **kwargs)

    def do_whisper(self, text: str, target, **kwargs):
        message = settings.ACTION_TEMPLATES.get("whisper")
        text_clean = ANSIString(text).clean()
        mapping = {"text": text, "text_clean": text_clean, "here": self.location, "target": target}
        self.do_action(message, delivery={}, mapping=mapping, targets=[target, self], **kwargs)

    def do_say(self, text: str, **kwargs):
        self._do_basic("say", text=text, delivery={}, **kwargs)

    def do_pose(self, text: str, **kwargs):
        self._do_basic("say", text=text, delivery={}, **kwargs)

    def do_semipose(self, text: str, **kwargs):
        self._do_basic("semipose", text=text, delivery={}, **kwargs)

    def do_emit(self, text: str, **kwargs):
        self._do_basic("emit", text=text, delivery={}, **kwargs)

    def send(self, text: str, extra_dict: typing.Optional[dict] = None, from_obj=None,
             mapping: typing.Optional[dict] = None, delivery: typing.Tuple[str] = None, options=None, **kwargs):
        """
        This method renders text templates in the same manner as DefaultObject.msg_contents and sends it to this
        object via .msg(). It is meant to be used as the termination point of all methods which generate in-character
        events/text, such as speech or actions or emits. Anything which is a noise, visual, sensor event, etc, should
        go through this method.

        It is recommended to create systems like Evennia's DefaultObject.at_say() which then call this, and have
        THOSE systems handle filtering, like who can hear a whisper through eavesdropping or so on.

        Args:
            text (str): The text to send to this object. This must be a string, not something that can be coerced
                into one.
            extra_dict (dict, optional): A dictionary that will be sent as the second argument of the text-tuple to
                .msg().
            from_obj (Object, optional): The object which is sending this text. This is used for formatting. If it's
                unclear who's sending the message, like a system event, this should be None.

        """
        if mapping is None:
            mapping = dict()

        outmessage = _MSG_CONTENTS_PARSER.parse(
            text,
            raise_errors=True,
            return_string=True,
            caller=from_obj if from_obj else self,
            receiver=self,
            mapping=mapping,
        )

        keys = SafeDict({
                key: obj.get_display_name(looker=self)
                if hasattr(obj, "get_display_name")
                else str(obj)
                for key, obj in mapping.items()
            })

        outmessage = ANSIString(outmessage.format_map(keys))

        self.msg(text=(outmessage, extra_dict) if extra_dict else outmessage, from_obj=from_obj,
                 options=options, delivery=delivery, **kwargs)
        if delivery:
            self.at_delivery(from_obj, mapping, )

    def all_modifier_slots(self) -> dict[str, dict]:
        """
        Replace this method with one for this typeclasses's modifier slots.
        """
        return dict()

    def all_equip_slots(self) -> dict[str, dict]:
        """
        Replace this method with one for this typeclasses's equip slots.
        """
        return dict()

    def available_equip_slots(self, **kwargs) -> dict[str, typing.Type["EquipSlot"]]:
        return {k: v for k, v in self.all_equip_slots() if v.is_available(self, **kwargs)}

    def get_equip_slots(self, skip_occupied=False, **kwargs) -> dict[str, typing.Type["EquipSlot"]]:
        if not skip_occupied:
            return self.available_equip_slots()
        return {k: v for k, v in self.available_equip_slots(**kwargs).items() if not self.equipment.get(k)}

    def get_equip_types(self, skip_occupied=False, **kwargs) -> dict[str, list[typing.Type["EquipSlot"]]]:
        out = defaultdict(list)
        for k, v in self.get_equip_slots(skip_occupied=skip_occupied, **kwargs).items():
            out[v.slot_type].append(v)
        return out

    def get_inventory(self) -> List["AthanorItem"]:
        """
        Returns a list of all items in the character's inventory.
        """
        return [item for item in self.contents_get(content_type="item") if item.db.equip_slot is None]

    def get_equipment(self) -> typing.Dict[str, "AthanorItem"]:
        """
        Returns a list of all items equipped by the character.
        """
        return self.equip.occupied()

    def init_effects(self):
        """
        Initializes the character's effects.

        This should iterate through all sources of Effects - such as equipped items, or character class,
        and add them to the character's non-persistent effects as appropriate.
        """
        pass


class AthanorItem(DefaultObject, AthanorBase):
    _content_types = ("item",)

    def is_equipped(self) -> bool:
        return bool(self.db.equip_slot)


class AthanorRoom(DefaultRoom, AthanorBase):
    """
    Not much different from Evennia DefaultRooms.
    """
    _content_types = ("room",)

    def at_pre_move(self, destination: Optional[DefaultObject], **kwargs):
        """
        Called just before moving object to destination.
        If returns False, move is cancelled.
        """
        if not destination:
            return False
        return "structure" in destination._content_types

    def at_object_receive(self, obj: DefaultObject, source_location: Optional[DefaultObject], move_type="move", **kwargs):
        """
        Called after an object has been moved into this object.

        Anything inside a Room is simply there.
        """
        del obj.db.coordinates


class _AthanorCharacter(DefaultCharacter, AthanorBase):
    """
    Abstract base class for Athanor characters.
    Do not instantiate directly.
    """
    _content_types = ("character",)

    def at_pre_move(self, destination: Optional[DefaultObject], **kwargs):
        """
        Called just before moving object to destination.
        If returns False, move is cancelled.
        """
        if not destination:
            return True

        # Characters may only exist inside Rooms, Sectors, or Grids.
        return any(ctype in destination._content_types for ctype in ("room", "grid", "sector"))

    def at_object_receive(self, obj: DefaultObject, source_location: Optional[DefaultObject], move_type="move", **kwargs):
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


class AthanorNonPlayerCharacter(_AthanorCharacter):
    """
    The base for all non-player characters.
    """
    is_player = False


class AthanorStructure(DefaultObject, AthanorBase):
    _content_types = ("structure",)

    def at_pre_move(self, destination: Optional[DefaultObject], **kwargs):
        """
        Called just before moving object to destination.
        If returns False, move is cancelled.
        """
        if not destination:
            return True

        # Characters may only exist inside Rooms, Sectors, or Grids.
        return any(ctype in destination._content_types for ctype in ("room", "grid", "sector"))


class AthanorExit(DefaultExit, AthanorBase):
    _content_types = ("exit",)

    def at_pre_move(self, destination: Optional[DefaultObject], **kwargs):
        """
        Called just before moving object to destination.
        If returns False, move is cancelled.
        """
        if destination and "room" not in destination._content_types:
            return False
        return True


class AthanorGrid(DefaultObject, AthanorBase):
    _content_types = ("grid",)

    def at_pre_move(self, destination: Optional[DefaultObject], **kwargs):
        """
        Called just before moving object to destination.
        If returns False, move is cancelled.
        """
        # Grids can't be anywhere.
        if not destination:
            return True

    def at_object_receive(self, obj: DefaultObject, source_location: Optional[DefaultObject], move_type="move", **kwargs):
        """
        Called after an object has been moved into this object.

        Anything inside a grid has X Y coordinates.
        """
        obj.db.coordinates = (0, 0)


class AthanorSector(DefaultObject, AthanorBase):
    _content_types = ("sector",)

    def at_pre_move(self, destination: Optional[DefaultObject], **kwargs):
        """
        Called just before moving object to destination.
        If returns False, move is cancelled.
        """
        # Sectors can't be anywhere.
        if not destination:
            return True

    def at_object_receive(self, obj: DefaultObject, source_location: Optional[DefaultObject], move_type="move", **kwargs):
        """
        Called after an object has been moved into this object.

        Anything inside a grid has X Y Z coordinates.
        """
        obj.db.coordinates = (0.0, 0.0, 0.0)

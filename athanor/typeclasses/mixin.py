import typing
from collections import defaultdict
from django.conf import settings
from typing import Optional, List
from evennia.utils.ansi import strip_ansi, ANSIString
from evennia.utils.utils import lazy_property
from athanor.utils import SafeDict, partial_match
from evennia.objects.objects import _MSG_CONTENTS_PARSER
from athanor.equip import EquipHandler
from athanor.aspects import AspectHandler
from athanor.quirks import QuirkHandler
from athanor.prompt import PromptHandler
from athanor.stats import StatHandler


class AthanorBase:
    """
    Mixin for general Athanor functionality.
    """

    format_kwargs = ("name", "desc", "header", "footer", "exits", "characters", "things")

    def return_appearance(self, looker, **kwargs):
        if not looker:
            return ""
        kwargs["contents_map"] = self.get_visible_contents(looker, **kwargs)
        out_dict = SafeDict()
        for k in self.format_kwargs:
            if (f_func := getattr(self, f"get_display_{k}", None)):
                if callable(f_func):
                    out_dict[k] = f_func(looker, **kwargs)
                else:
                    out_dict[k] = f_func
        return self.format_appearance(self.appearance_template.format_map(out_dict), looker, **kwargs)


    @lazy_property
    def equip(self):
        return EquipHandler(self)

    @lazy_property
    def aspects(self):
        return AspectHandler(self)

    @lazy_property
    def quirks(self):
        return QuirkHandler(self)

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
        pass  # self.dgscripts.trigger_speech(speech, from_obj, **kwargs)

    def at_see(self, text, from_obj, msg_type, extra, **kwargs):
        pass  # self.dgscripts.trigger_act(strip_ansi(text), from_obj, **kwargs)

    def has_active_sessions(self):
        return bool(self.sessions.all())

    def at_post_move(self, source_location, move_type="move", **kwargs):
        """
        We make sure to look around after a move.

        """
        if not self.has_active_sessions():
            return
        super().at_post_move(source_location, move_type, **kwargs)

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

    def all_quirk_slots(self) -> dict[str, dict]:
        return dict()

    def all_aspect_slots(self) -> dict[str, dict]:
        """
        Replace this method with one for this typeclasses's trait slots.
        """
        return dict()

    def all_equip_slots(self) -> dict[str, dict]:
        """
        Replace this method with one for this typeclasses's equip slots.
        """
        return dict()

    def at_equip_item(self, item, slot, **kwargs):
        """
        Called by the EquipSlot after an item has been equipped.
        This is mostly useful for making echos. It's not recommended to do
        anything mechanically heavy here.
        """
        pass

    def on_equip(self, owner, slot, **kwargs):
        """
        Called by the EquipSlot on an item after it has been equipped.
        This is most useful for applying Effects and similar shenanigans.
        """
        pass

    def at_remove_item(self, item, slot, **kwargs):
        """
        Called by the EquipSlot after an item has been removed.
        This is mostly useful for making echos. It's not recommended to do
        anything mechanically heavy here.
        """
        pass

    def on_remove(self, owner, slot, **kwargs):
        """
        Called by the EquipSlot on an item after it has been removed.
        This is most useful for applying Effects and similar shenanigans.
        """
        pass

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

    def init_effects(self):
        """
        Initializes the character's effects.

        This should iterate through all sources of Effects - such as equipped items, or character class,
        and add them to the character's non-persistent effects as appropriate.
        """
        pass

    @lazy_property
    def prompt(self):
        return PromptHandler(self)

    def render_prompt(self, looker) -> str:
        """
        Render the prompt for this Object.
        """
        pass

    def generate_keywords(self, looker, **kwargs) -> typing.Set[str]:
        """
        This should return a set of keywords that can be used to search for this object.

        The object searching for it is included to handle dynamic generation of keywords
        based on perspective.
        """
        results = set()

        for alias in self.aliases.all():
            for word in alias.split():
                results.add(word.lower())
        for word in self.key.split():
            results.add(word.lower())
        return results

    def check_search_match(self, looker, ostring: str, exact: bool, **kwargs):
        keywords = self.generate_keywords(looker, **kwargs)
        if exact:
            return ostring.lower() in keywords
        return bool(partial_match(ostring, keywords))

    def get_list_display_for(self, obj, looker, **kwargs):
        return obj.get_display_name(looker=looker, **kwargs)

    def get_display_name(self, looker=None, **kwargs) -> str:
        """
        Returns the name of the object to looker.

        Args:
            looker (Object, optional): The object looking at this object.
        """
        return self.attributes.get(key="short_description", default=self.key).strip("|/")

    @lazy_property
    def stats(self):
        return StatHandler(self, self._content_types)

    def filter_visible(self, candidates) -> list["AthanorItem"]:
        return [c for c in candidates if self.can_see(c)]

    def get_visible_nearby(self, obj_type: str=None):
        candidates = []

        match obj_type:
            case "exit":
                candidates.extend(self.location.exits)
            case "item":
                candidates.extend(self.location.get_inventory())
            case _:
                if (check_func := getattr(self, f"get_visible_nearby_{obj_type}", None)) is not None and callable(check_func):
                    candidates.extend(check_func())
                elif isinstance(obj_type, str):
                    candidates.extend(self.location.contents_get(content_type=obj_type))

        candidates.remove(self)
        return self.filter_visible(candidates)


    def get_room_display_name(self, looker=None, **kwargs) -> str:
        """
        Returns the name of the object to looker.

        Args:
            looker (Object, optional): The object looking at this object.
        """
        return self.get_display_name(looker=looker, **kwargs)
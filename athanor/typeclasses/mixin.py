import typing
from collections import defaultdict
from django.conf import settings
from typing import Optional, List
from evennia.utils import logger, make_iter, to_str
from evennia.utils.ansi import strip_ansi, ANSIString
from evennia.utils.utils import lazy_property
from athanor.utils import SafeDict, partial_match
from athanor.mudrich import MudText
from evennia.objects.objects import _MSG_CONTENTS_PARSER
from athanor.equip import EquipHandler
from athanor.traits import TraitHandler
from athanor.prompt import PromptHandler
from athanor.stats import StatHandler


class AthanorBase:
    """
    Mixin for general Athanor functionality.
    """

    @lazy_property
    def equip(self):
        return EquipHandler(self)

    @lazy_property
    def traits(self):
        return TraitHandler(self)

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

    def all_trait_slots(self) -> dict[str, dict]:
        """
        Replace this method with one for this typeclasses's trait slots.
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

    def init_effects(self):
        """
        Initializes the character's effects.

        This should iterate through all sources of Effects - such as equipped items, or character class,
        and add them to the character's non-persistent effects as appropriate.
        """
        pass

    def msg(self, text=None, from_obj=None, session=None, options=None, **kwargs):
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
        Keyword Args:
            any (string or tuples): All kwarg keys not listed above
                will be treated as send-command names and their arguments
                (which can be a string or a tuple).

        Notes:
            `at_msg_receive` will be called on this Object.
            All extra kwargs will be passed on to the protocol.

        """
        # try send hooks
        if from_obj:
            for obj in make_iter(from_obj):
                try:
                    obj.at_msg_send(text=text, to_obj=self, **kwargs)
                except Exception:
                    logger.log_trace()
        kwargs["options"] = options

        highlight = options.get("highlight", False)

        try:
            if not self.at_msg_receive(text=text, from_obj=from_obj, **kwargs):
                # if at_msg_receive returns false, we abort message to this object
                return
        except Exception:
            logger.log_trace()

        if text is not None:
            extra = None
            if isinstance(text, tuple):
                t = text[0]
                extra = text[1]
            else:
                t = text
            if not isinstance(t, str):
                if not hasattr(t, "__rich_console__"):
                    if not isinstance(t, (list, tuple)):
                        # sanitize text before sending across the wire
                        try:
                            t = to_str(text)
                        except Exception:
                            t = repr(text)
            else:
                if highlight:
                    t = MudText(t)
            kwargs["text"] = t if extra is None else (t, extra)
            if settings.PROMPT_ENABLED and not kwargs.pop("noprompt", False):
                self.prompt.prepare(prompt_delay=settings.PROMPT_DELAY)

        # relay to session(s)
        sessions = make_iter(session) if session else self.sessions.all()
        for session in sessions:
            session.data_out(**kwargs)

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

    def search(self, *args, **kwargs):
        self.objects.looker = self
        results = super().search(*args, **kwargs)
        del self.objects.looker
        return results

    def get_display_name(self, looker=None, **kwargs) -> str:
        """
        Returns the name of the object to looker.

        Args:
            looker (Object, optional): The object looking at this object.
        """
        name = self.attributes.get(key="short_description", default=self.key)
        if looker and self.locks.check_lockstring(looker, "perm(Builder)"):
            return f"{name}(#{self.id})"
        return name

    @lazy_property
    def stats(self):
        return StatHandler(self, self._content_types)

import typing
from typing import Optional, List
from collections import defaultdict

from django.conf import settings

from evennia.utils.ansi import strip_ansi, ANSIString
from evennia.utils.utils import lazy_property
from evennia.objects.objects import _MSG_CONTENTS_PARSER

import athanor
from athanor.utils import SafeDict, partial_match


class AthanorAccess:
    lock_access_funcs = defaultdict(list)

    def access(
        self,
        accessing_obj,
        access_type="read",
        default=False,
        no_superuser_bypass=False,
        call_hooks=True,
        call_funcs=True,
        call_super=True,
        **kwargs,
    ):
        result = (
            super().access(
                accessing_obj,
                access_type=access_type,
                default=default,
                no_superuser_bypass=no_superuser_bypass,
                **kwargs,
            )
            if call_super
            else default
        )
        if result:
            return result
        if call_hooks:
            if callable(
                hook := getattr(
                    self, f"access_check_{access_type.replace(' ', '_')}", None
                )
            ):
                if hook(accessing_obj, **kwargs):
                    return True
        if call_funcs:
            if funcs := self.lock_access_funcs.get(access_type, list()):
                for func in funcs:
                    if func(self, accessing_obj, **kwargs):
                        return True
        return False


class AthanorLowBase(AthanorAccess):
    msg_parser = _MSG_CONTENTS_PARSER

    def render_system_header(self, header: str) -> str:
        return f"|n|m-=<|n|w{header}|n|m>=-|n"

    def system_send(
        self,
        header: str,
        template: str,
        extra_dict: typing.Optional[dict] = None,
        from_obj=None,
        mapping: typing.Optional[dict] = None,
        delivery: typing.Tuple[str] = None,
        options=None,
        **kwargs,
    ):
        if mapping is None:
            mapping = dict()

        outmessage = _MSG_CONTENTS_PARSER.parse(
            template,
            raise_errors=True,
            return_string=True,
            caller=from_obj if from_obj else self,
            receiver=self,
            mapping=mapping,
        )

        keys = SafeDict(
            {
                key: obj.get_display_name(looker=self)
                if hasattr(obj, "get_display_name")
                else str(obj)
                for key, obj in mapping.items()
            }
        )

        outmessage = ANSIString(
            f"{self.render_system_header(header)} {outmessage.format_map(keys)}"
        )

        self.msg(
            text=(outmessage, extra_dict) if extra_dict else outmessage,
            from_obj=from_obj,
            options=options,
            delivery=delivery,
            **kwargs,
        )


class AthanorBase(AthanorLowBase):
    """
    Mixin for general Athanor functionality.
    """

    format_kwargs = (
        "name",
        "desc",
        "header",
        "footer",
        "exits",
        "characters",
        "things",
    )
    lock_access_funcs = athanor.OBJECT_ACCESS_FUNCTIONS

    def return_appearance(self, looker, **kwargs):
        if not looker:
            return ""
        kwargs["contents_map"] = self.get_visible_contents(looker, **kwargs)
        out_dict = SafeDict()
        for k in self.format_kwargs:
            if f_func := getattr(self, f"get_display_{k}", None):
                if callable(f_func):
                    out_dict[k] = f_func(looker, **kwargs)
                else:
                    out_dict[k] = f_func
        return self.format_appearance(
            self.appearance_template.format_map(out_dict), looker, **kwargs
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
        speech = text[first_quote + 1 : -1]
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

    def do_action(
        self, template: str, delivery: dict, mapping: dict, targets: list, **kwargs
    ):
        """
        Distribute a format-message as self to targets.
        """
        for target in targets:
            if target.check_delivery(self, template, delivery, mapping):
                target.send(
                    template,
                    extra_dict=delivery,
                    mapping=mapping,
                    from_obj=self,
                    **kwargs,
                )

    def _do_basic(self, mode: str, text: str, delivery: dict, **kwargs):
        if not self.location:
            self.msg("You can't do that here... you are nowhere.")
            return
        message = settings.ACTION_TEMPLATES.get(mode)
        text_clean = ANSIString(text).clean()
        mapping = {"text": text, "text_clean": text_clean, "here": self.location}
        self.do_action(
            message,
            delivery=delivery,
            mapping=mapping,
            targets=self.location.contents,
            **kwargs,
        )

    def do_whisper(self, text: str, target, **kwargs):
        message = settings.ACTION_TEMPLATES.get("whisper")
        text_clean = ANSIString(text).clean()
        mapping = {
            "text": text,
            "text_clean": text_clean,
            "here": self.location,
            "target": target,
        }
        self.do_action(
            message, delivery={}, mapping=mapping, targets=[target, self], **kwargs
        )

    def do_say(self, text: str, **kwargs):
        self._do_basic("say", text=text, delivery={}, **kwargs)

    def do_pose(self, text: str, **kwargs):
        self._do_basic("say", text=text, delivery={}, **kwargs)

    def do_semipose(self, text: str, **kwargs):
        self._do_basic("semipose", text=text, delivery={}, **kwargs)

    def do_emit(self, text: str, **kwargs):
        self._do_basic("emit", text=text, delivery={}, **kwargs)

    def send(
        self,
        text: str,
        extra_dict: typing.Optional[dict] = None,
        from_obj=None,
        mapping: typing.Optional[dict] = None,
        delivery: typing.Tuple[str] = None,
        options=None,
        **kwargs,
    ):
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

        keys = SafeDict(
            {
                key: obj.get_display_name(looker=self)
                if hasattr(obj, "get_display_name")
                else str(obj)
                for key, obj in mapping.items()
            }
        )

        outmessage = ANSIString(outmessage.format_map(keys))

        self.msg(
            text=(outmessage, extra_dict) if extra_dict else outmessage,
            from_obj=from_obj,
            options=options,
            delivery=delivery,
            **kwargs,
        )
        if delivery:
            self.at_delivery(
                from_obj,
                mapping,
            )

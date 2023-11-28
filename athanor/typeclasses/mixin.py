import typing
from typing import Optional, List
from collections import defaultdict

from django.conf import settings

from evennia.utils import logger, lazy_property, make_iter, to_str
from evennia.utils.ansi import strip_ansi, ANSIString
from evennia.objects.objects import _MSG_CONTENTS_PARSER

import athanor
from athanor.utils import SafeDict, partial_match, split_oob
from athanor.lockhandler import AthanorLockHandler

_CMDHANDLER = None


class PlayviewSessionHandler:
    """
    A dummy handler for Objects which relays session-related commands to the Playview.

    """

    def __init__(self, obj):
        self.obj = obj

    @property
    def _playview(self):
        if pv := getattr(
            self.obj, "puppeting_playview", getattr(self.obj, "playview", None)
        ):
            return pv
        return None

    def get(self, sessid=None):
        if not (pv := self._playview):
            return None
        return pv.sessions.get(sessid=sessid)

    def all(self):
        if not (pv := self._playview):
            return []
        return pv.sessions.all()

    def add(self, session):
        if not (pv := self._playview):
            return
        pv.add_session(session)

    def remove(self, session):
        if not (pv := self._playview):
            return
        pv.remove_session(session)

    def clear(self):
        if not (pv := self._playview):
            return
        pv.sessions.clear()

    def count(self):
        if not (pv := self._playview):
            return 0
        return pv.sessions.count()


class Handlers:
    def __init__(self, obj):
        self.obj = obj
        self.handlers: dict[str, "Handler"] = dict()
        self.loaded = False

    @property
    def owner(self):
        return self.obj

    def __contains__(self, item):
        if item in self.handlers:
            return True
        for content_type in reversed(getattr(self.obj, "_content_types", list())):
            if content_type not in athanor.HANDLERS:
                continue
            if item in athanor.HANDLERS[content_type]:
                return True
        return False

    def __getattr__(self, item):
        try:
            return self[item]
        except KeyError as err:
            raise AttributeError(str(err))

    def __getitem__(self, item):
        if item in self.handlers:
            return self.handlers[item]
        for content_type in reversed(getattr(self.obj, "_content_types", list())):
            if content_type not in athanor.HANDLERS:
                continue
            if handler_class := athanor.HANDLERS[content_type].get(item):
                try:
                    handler = handler_class(self.owner)
                except Exception as err:
                    raise KeyError(str(err))
                self.handlers[item] = handler
                return handler
        raise KeyError(f"No handler found for '{item}'.")

    def load(self):
        if self.loaded:
            return
        self.loaded = True
        for content_type in reversed(getattr(self.obj, "_content_types", list())):
            if content_type not in athanor.HANDLERS:
                continue
            for handler_key, handler_path in athanor.HANDLERS[content_type].items():
                if handler_key in self.handlers:
                    continue
                try:
                    handler = handler_path(self.owner)
                    self.handlers[handler_key] = handler
                except Exception as err:
                    self.obj.msg(f"Error loading handler '{handler_key}': {err}")

    def __iter__(self):
        self.load()
        return iter(self.handlers.values())

    def all(self):
        self.load()
        return list(self.handlers.values())


class AthanorHandler:
    @lazy_property
    def handlers(self):
        return Handlers(self)

    @property
    def h(self):
        return self.handlers


class AthanorAccess:
    lock_access_funcs = defaultdict(list)
    lock_default_funcs = defaultdict(list)

    @lazy_property
    def locks(self):
        return AthanorLockHandler(self)

    def get_lockdef(self, access_type: str):
        """
        Retrieves the lockstring for the given access type.
        """
        for func in self.lock_default_funcs.get(access_type, list()):
            if callable(func):
                func = func(self, access_type)
            if isinstance(func, str):
                func = self.locks._parse_lockstring(f"{access_type}:{func}")[
                    access_type
                ]
            if isinstance(func, (tuple, list)):
                return func
        return None

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
        access_type = access_type.lower()
        if result := (
            super().access(
                accessing_obj,
                access_type=access_type,
                default=default,
                no_superuser_bypass=no_superuser_bypass,
                **kwargs,
            )
            if call_super
            else default
        ):
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
                    if callable(func) and func(
                        self, accessing_obj, access_type, **kwargs
                    ):
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


class AthanorMessage:
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

    def _msg_helper_format(self, **kwargs):
        """
        Helper method that formats the text kwarg for sending.

        Args:
            text (str or None): A string object or something that can be coerced into a string.
            kwargs: The outputfuncs dictionary being built up for this .msg() operation.
        """
        out_kwargs = dict()

        for k, v in kwargs.items():
            match k:
                case "options":
                    if v:
                        out_kwargs[k] = v
                case _:
                    data, options = split_oob(v)
                    if callable(render := getattr(data, "render", None)):
                        data = render(self, options)
                    out_kwargs[k] = (data, options)

        return out_kwargs

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

    def at_msg_receive(self, text=None, from_obj=None, **kwargs):
        return True

    def at_post_msg_receive(self, from_obj=None, **kwargs):
        """
        Overloadable hook which receives the kwargs that exist at the tail end of self.msg()'s processing.

        This might be used for logging and similar purposes.

        Kwargs:
            from_obj (DefaultObject or list[DefaultObject]): The objects that sent the message.
            **kwargs: The kwargs from the end of message, using the Evennia outputfunc format.
        """
        for t in getattr(self, "_content_types", list()):
            athanor.EVENTS[f"{t}_at_post_msg_receive"].send(
                sender=self, from_obj=from_obj, **kwargs
            )

    def msg(
        self,
        text=None,
        from_obj=None,
        session=None,
        options=None,
        source=None,
        **kwargs,
    ):
        if options:
            kwargs["options"] = options
        if text is not None:
            kwargs["text"] = text
        kwargs = self._msg_helper_format(**kwargs)

        # try send hooks
        self._msg_helper_from_obj(from_obj=from_obj, **kwargs)

        if not self._msg_helper_receive(from_obj=from_obj, **kwargs):
            return

        # relay to session(s)
        self._msg_helper_session_relay(session=session, **kwargs)

        self.at_post_msg_receive(from_obj=from_obj, **kwargs)

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


class AthanorObject(AthanorMessage, AthanorHandler, AthanorBase):
    lock_access_funcs = athanor.OBJECT_ACCESS_FUNCTIONS

    # Determines which order command sets begin to be assembled from.
    # Objects are usually fourth.
    cmd_order = 100
    cmd_order_error = 100
    cmd_type = "object"

    def get_command_objects(self) -> dict[str, "CommandObject"]:
        """
        Overrideable method which returns a dictionary of all the kinds of CommandObjects
        linked to this Object.
        In all normal cases, that's the Object itself, and maybe an Account if the Object
        is being puppeted.
        The cmdhandler uses this to determine available cmdsets when executing a command.
        Returns:
            dict[str, CommandObject]: The CommandObjects linked to this Object.
        """
        out = {"object": self}
        if self.account:
            out["account"] = self.account

        if pv := getattr(self, "puppeted_playview", getattr(self, "playview", None)):
            out["playview"] = pv

        return out

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

    @property
    def is_player(self):
        return False

    def uses_screenreader(self, session=None):
        if not self.account:
            return False
        return self.account.uses_screenreader(session=session)

    def get_room_display_name(self, looker, **kwargs):
        return self.get_display_name(looker, **kwargs)

    def at_total_playtime_update(self, new_total: int):
        """
        This is called every time the total playtime is updated.
        You could use this to enforce all kinds of rules,
        or maybe for veteran rewards.
        """
        pass

    def at_account_playtime_update(self, account, new_total: int):
        """
        This is called every time the playtime is updated per-account.
        You could use this to enforce all kinds of rules,
        or maybe for veteran rewards.

        Args:
            account (Account): The account whose playtime was updated.
            new_total (int): The new total playtime for this account.
        """
        pass

    @property
    def playtime(self):
        from athanor.models import CharacterPlaytime

        return CharacterPlaytime.objects.get_or_create(id=self)[0]

    def get_playtime(self, account=None) -> int:
        """
        Returns the total playtime for this character, optionally for a specific account.
        """
        p = self.playtime
        if account:
            ca = p.per_account.filter(account=account).first()
            if ca:
                return ca.total_playtime
            return 0
        return p.total_playtime

    @property
    def idle_time(self):
        """
        Returns the idle time of the least idle session in seconds. If
        no sessions are connected it returns nothing.

        """
        if not (playview := getattr(self, "playview", None)):
            return None
        return playview.idle_time

    @property
    def connection_time(self):
        """
        Returns the maximum connection time of all connected sessions
        in seconds. Returns nothing if there are no sessions.

        """
        if not (playview := getattr(self, "playview", None)):
            return None
        return playview.date_created

    @lazy_property
    def sessions(self):
        return PlayviewSessionHandler(self)

    def at_object_creation(self):
        pass

    def execute_cmd(self, raw_string, session=None, **kwargs):
        # break circular import issues
        global _CMDHANDLER
        if not _CMDHANDLER:
            from athanor.cmdhandler import cmdhandler as _CMDHANDLER

        # nick replacement - we require full-word matching.
        # do text encoding conversion
        raw_string = self.nicks.nickreplace(
            raw_string, categories=("inputline", "channel"), include_account=True
        )
        return _CMDHANDLER(
            self, raw_string, callertype="object", session=session, **kwargs
        )

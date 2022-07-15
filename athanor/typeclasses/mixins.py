import typing
from itertools import chain
from django.core.exceptions import ObjectDoesNotExist
from evennia.utils.utils import lazy_property, make_iter, to_str, logger
from athanor.commands.queue import CmdQueueHandler
from athanor.handlers import InventoryHandler, EquipmentHandler, WeightHandler, PeopleHandler, HangarHandler
from athanor.utils import ev_to_rich
from evennia.utils.ansi import strip_ansi
from athanor.dgscripts.dgscripts import DGHandler, DGCommand, MobTriggers
from twisted.internet.defer import inlineCallbacks, returnValue
from evennia import CmdSet


class AthanorObj:
    cmd_objects_sort_priority = 100

    # This field should contain string names of properties on this object
    # which provide an .all() method that returns an iterable of Modifiers.
    # Order according to preference.
    modifier_attrs = []

    def get_cmd_objects(self):
        if (puppeteer := self.get_puppeteer()):
            return puppeteer.get_cmd_objects()
        return {"puppet": self}

    def generate_dg_commands(self):
        dg_cmdset = CmdSet()
        dg_cmdset.key = "DGCmdSet"
        dg_cmdset.duplicates = False
        dg_cmdset.old_duplicates = False
        for k, v in self.dgscripts.scripts.items():
            if v.proto.db_trigger_type & MobTriggers.COMMAND:
                dg_cmdset.add(DGCommand(key=v.proto.arglist, script_id=k, obj=self))
        return dg_cmdset


    @inlineCallbacks
    def get_location_cmdsets(self, caller, current, cmdsets):
        """
        Retrieve Cmdsets from nearby Objects.
        """
        try:
            location = self.location
        except Exception:
            location = None

        if not location:
            returnValue(list())

        local_objlist = yield (
                location.contents_get(exclude=self) + self.contents_get() + [location]
        )
        local_objlist = [o for o in local_objlist if not o._is_deleted]
        for lobj in local_objlist:
            try:
                # call hook in case we need to do dynamic changing to cmdset
                object.__getattribute__(lobj, "at_cmdset_get")(caller=caller)
            except Exception:
                logger.log_trace()
        # the call-type lock is checked here, it makes sure an account
        # is not seeing e.g. the commands on a fellow account (which is why
        # the no_superuser_bypass must be True)
        local_obj_cmdsets = yield list(
            chain.from_iterable(
                lobj.cmdset.cmdset_stack
                for lobj in local_objlist
                if (lobj.cmdset.current and lobj.access(caller, access_type="call", no_superuser_bypass=True))
            )
        )
        for cset in local_obj_cmdsets:
            # This is necessary for object sets, or we won't be able to
            # separate the command sets from each other in a busy room. We
            # only keep the setting if duplicates were set to False/True
            # explicitly.
            cset.old_duplicates = cset.duplicates
            cset.duplicates = True if cset.duplicates is None else cset.duplicates

        if current.no_exits:
            local_obj_cmdsets = [
                cmdset for cmdset in local_obj_cmdsets if cmdset.key != "ExitCmdSet"
            ]

        returnValue((local_obj_cmdsets, local_objlist))

    @inlineCallbacks
    def get_extra_cmdsets(self, caller, current, cmdsets):
        """
        Called by the CmdHandler to retrieve extra cmdsets from this object.
        For DefaultObject, that's cmdsets from nearby Objects.
        """
        extra = list()
        if not current.no_objs:
            obj_cmdsets, local_objlist = yield self.get_location_cmdsets(caller, current, cmdsets)
            extra.extend(obj_cmdsets)
            extra.extend([obj.generate_dg_commands() for obj in local_objlist])
        returnValue(extra)

    @lazy_property
    def cmdqueue(self):
        """
        Used by QueueCommands that are pending execution.
        """
        return CmdQueueHandler(self)

    def get_all_modifiers(self):
        """
        A Generator that will iterate over all Modifiers affecting this object.
        """
        for attr in self.modifier_attrs:
            if hasattr(self, attr):
                for m in getattr(self, attr).all():
                    yield m

    @lazy_property
    def inventory(self):
        return InventoryHandler(self)

    @lazy_property
    def people(self):
        return PeopleHandler(self)

    @lazy_property
    def vehicles(self):
        return HangarHandler(self)

    @lazy_property
    def equipment(self):
        return EquipmentHandler(self)

    @lazy_property
    def weight(self):
        return WeightHandler(self)

    def max_carry_weight(self, exist_value=None) -> float:
        return 9999999999999999999999999999.0

    def available_carry_weight(self, exist_value=None) -> float:
        return self.max_carry_weight(exist_value=exist_value) - self.weight.burden()

    def at_object_leave(self, moved_obj, target_location, **kwargs):
        match moved_obj.obj_type:
            case "character":
                self.people.remove(moved_obj)
            case "vehicle":
                self.vehicles.remove(moved_obj)
            case "item":
                if moved_obj.db.equipped:
                    self.equipment.remove(moved_obj.db.equipped[1])
                else:
                    self.inventory.remove(moved_obj)

    def at_object_receive(self, moved_obj, source_location, **kwargs):
        match moved_obj.obj_type:
            case "character":
                self.people.add(moved_obj)
            case "item":
                self.inventory.add(moved_obj)
            case "vehicle":
                self.vehicles.add(moved_obj)

    def ignore_equipped_weight(self):
        return False

    def ignore_carried_weight(self):
        return False

    def can_carry_anything(self):
        return self.locks.check_lockstring(self, "perm(Builder)")

    carry_checks = ["carry_check_weight"]

    def carry_check_weight(self, obj, **kwargs) -> typing.Optional[str]:
        obj_weight = obj.weight.total()
        if obj_weight > self.available_carry_weight():
            return "can't carry that much weight!"

    def can_carry_object(self, obj, quiet=False, **kwargs):
        reasons = list()
        for check in self.carry_checks:
            if (func := getattr(self, check, None)):
                if (reason := func(obj)):
                    reasons.append(reason)
        if reasons:
            if self.can_carry_anything():
                if not quiet:
                    self.msg(ev_to_rich(f"Your buildpowers enable you to carry {obj.get_display_name(looker=self)} despite: {', '.join(reasons)}"))
                return True
            else:
                if not quiet:
                    self.msg(ev_to_rich(f"You can't carry {obj.get_display_name(looker=self)} because: {', '.join(reasons)}"))
                return False
        else:
            return True

    take_checks = []

    def can_be_taken(self, getter, quiet=False, **kwargs):
        reasons = list()
        for check in self.take_checks:
            if (func := getattr(self, check, None)):
                if (reason := func(getter)):
                    reasons.append(reason)

        if reasons:
            if self.can_carry_anything():
                if not quiet:
                    getter.msg(ev_to_rich(f"Your buildpowers enable you to carry {self.get_display_name(looker=getter)} despite: {', '.join(reasons)}"))
                return True
            else:
                if not quiet:
                    getter.msg(ev_to_rich(f"You can't carry {self.get_display_name(looker=getter)} because: {', '.join(reasons)}"))
                return False
        else:
            return True

    def at_pre_get(self, getter, **kwargs):
        if not self.can_be_taken(getter, **kwargs):
            return False
        if not getter.can_carry_object(self, quiet=False):
            return False
        return True

    def at_pre_equip(self, user, slot, **kwargs):
        """
        Called by the equip command and works exactly like the at_pre_get hook.
        """
        return False

    def equip_to(self, user, slot: int, equip_hooks = True, quiet = False, **kwargs):

        old_loc = self.location

        if old_loc and old_loc != user:
            old_loc.at_object_leave(self, user)

        if equip_hooks:
            user.at_object_equip(self, slot, **kwargs)
        if not quiet:
            self.announce_equip_to(user, slot, **kwargs)

        user.inventory.remove(self)

        # This will set self.location too.
        user.equipment.equip(slot, self)

        if equip_hooks:
            self.at_post_equip(user, slot, **kwargs)

    def announce_equip_to(self, user, slot: int, **kwargs):
        pass

    def at_object_equip(self, item, slot: int, **kwargs):
        pass

    def at_post_equip(self, user, slot: int, **kwargs):
        pass

    def get_play(self):
        try:
            if hasattr(self, "play") and not self.play.db_account:
                return self.play
        except ObjectDoesNotExist:
            return None

    def get_puppeteer(self):
        try:
            if hasattr(self, "puppeteer") and self.puppeteer.db_account:
                return self.puppeteer
        except ObjectDoesNotExist:
            return None

    def msg(self, text=None, from_obj=None, session=None, options=None, **kwargs):
        # try send hooks
        if from_obj:
            for obj in make_iter(from_obj):
                try:
                    obj.at_msg_send(text=text, to_obj=self, **kwargs)
                except Exception:
                    logger.log_trace()
        kwargs["options"] = options
        try:
            if not self.at_msg_receive(text=text, from_obj=from_obj, **kwargs):
                # if at_msg_receive returns false, we abort message to this object
                return
        except Exception:
            logger.log_trace()

        if text is not None:
            if not isinstance(text, str):
                if isinstance(text, tuple):
                    first = text[0]
                    if hasattr(first, "__rich_console__"):
                        text = first
                    elif isinstance(first, str):
                        text = first
                    else:
                        try:
                            text = to_str(first)
                        except Exception:
                            text = repr(first)
                elif hasattr(text, "__rich_console__"):
                    text = text
                else:
                    try:
                        text = to_str(text)
                    except Exception:
                        text = repr(text)

        # relay to Play object
        if (puppeteer := self.get_puppeteer()):
            puppeteer.msg(text=text, session=session, **kwargs)

    def at_msg_type_say(self, text, from_obj, msg_type, extra, **kwargs):
        if not self.can_hear(from_obj):
            return False
        self.at_hear(text, from_obj, msg_type, extra, **kwargs)
        return True

    def at_msg_type_whisper(self, text, from_obj, msg_type, extra, **kwargs):
        return self.at_msg_type_say(text, from_obj, extra, **kwargs)

    def at_msg_type_pose(self, text, from_obj, msg_type, extra, **kwargs):
        if not self.can_see(from_obj):
            return False
        self.at_see(text, from_obj, msg_type, extra, **kwargs)
        return True

    def at_msg_type(self, text, from_obj, msg_type, extra, **kwargs):
        if (func := getattr(self, f"at_msg_type_{msg_type}", None)):
            return func(text, from_obj, msg_type, extra, **kwargs)
        return True

    def at_msg_receive(self, text=None, from_obj=None, **kwargs):
        # We only care if there's extra data attached to this text.
        if not isinstance(text, tuple):
            return True
        if not from_obj:
            return True

        t = text[0]
        m = text[1]

        if not (msg_type := m.get("type", None)):
            return True

        return self.at_msg_type(text[0], from_obj, msg_type, text[1], **kwargs)

    def can_hear(self, target):
        return True

    def can_see(self, target):
        return True

    def can_detect(self, target):
        return self.can_see(target) or self.can_hear(target)

    def at_hear(self, text, from_obj, msg_type, extra, **kwargs):
        text = strip_ansi(text)
        first_quote = text.find('"')
        speech = text[first_quote+1:-1]
        self.dgscripts.trigger_speech(speech, from_obj, **kwargs)

    def at_see(self, text, from_obj, msg_type, extra, **kwargs):
        self.dgscripts.trigger_act(strip_ansi(text), from_obj, **kwargs)

    @lazy_property
    def dgscripts(self):
        return DGHandler(self)

    @property
    def is_connected(self):
        return (play := self.get_play()) or (puppeteer := self.get_puppeteer())

    @property
    def has_account(self):
        return self.is_connected

    @property
    def is_superuser(self):
        if (play := self.get_play()) and play.is_superuser:
            return True
        if (puppeteer := self.get_puppeteer()) and puppeteer.is_superuser:
            return True
        return False

    @property
    def idle_time(self):
        """
        Returns the idle time of the least idle session in seconds. If
        no sessions are connected it returns nothing.

        """
        if (play := self.get_play()):
            return play.idle_time
        if (puppeteer := self.get_puppeteer()):
            return puppeteer.idle_time
        return None

    @property
    def connection_time(self):
        if (play := self.get_play()):
            return play.connection_time
        if (puppeteer := self.get_puppeteer()):
            return puppeteer.connection_time
        return None

    def at_possess(self, play):
        pass

    def at_unpossess(self, play):
        pass

    def at_give(self, giver, getter, **kwargs):
        self.dgscripts.trigger_given(giver, getter, **kwargs)
        giver.dgscripts.trigger_gave_item(self, getter, **kwargs)
        getter.dgscripts.trigger_gifted_item(self, giver, **kwargs)
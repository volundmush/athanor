import typing
from evennia.utils.utils import lazy_property, make_iter, to_str, logger
from athanor.commands.queue import CmdQueueHandler
from athanor.handlers import InventoryHandler, EquipmentHandler, WeightHandler
from athanor.utils import ev_to_rich
from athanor.dgscripts.dgscripts import DGHandler


class AthanorObj:
    # This field should contain string names of properties on this object
    # which provide an .all() method that returns an iterable of Modifiers.
    # Order according to preference.
    modifier_attrs = []

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
        if moved_obj.db.equipped:
            self.equipment.remove(moved_obj.db.equipped)
        else:
            self.inventory.remove(moved_obj)

    def at_object_receive(self, moved_obj, source_location, **kwargs):
        self.inventory.add(moved_obj)

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
                        kwargs["text"] = first
                    elif isinstance(first, str):
                        kwargs["text"] = first
                    else:
                        try:
                            kwargs["text"] = to_str(first)
                        except Exception:
                            kwargs["text"] = repr(first)
                elif hasattr(text, "__rich_console__"):
                    kwargs["text"] = text
                else:
                    try:
                        kwargs["text"] = to_str(text)
                    except Exception:
                        kwargs["text"] = repr(text)
            else:
                kwargs["text"] = text

        # relay to Play object
        if hasattr(self, "puppeteer"):
            self.puppeteer.msg(**kwargs)

    @lazy_property
    def dgscripts(self):
        return DGHandler(self)

    @property
    def is_connected(self):
        return hasattr(self, "play") or hasattr(self, "puppeteer")

    @property
    def has_account(self):
        return self.is_connected

    @property
    def is_superuser(self):
        if hasattr(self, "play") and self.play.is_superuser:
            return True
        if hasattr(self, "puppeteer") and self.puppeteer.is_superuser:
            return True
        return False

    @property
    def idle_time(self):
        """
        Returns the idle time of the least idle session in seconds. If
        no sessions are connected it returns nothing.

        """
        if hasattr(self, "play"):
            return self.play.idle_time
        if hasattr(self, "puppeteer"):
            return self.puppeteer.idle_time
        return None

    @property
    def connection_time(self):
        if hasattr(self, "play"):
            return self.play.connection_time
        if hasattr(self, "puppeteer"):
            return self.puppeteer.connection_time
        return None
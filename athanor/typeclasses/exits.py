"""
Exits

Exits are connectors between Rooms. An exit always has a destination property
set and has a single command defined on itself with the same name as its key,
for allowing Characters to traverse the exit to its destination.

"""
from evennia import DefaultExit
from .mixins import AthanorObj
from athanor.typing import ExitDir

class AthanorExit(AthanorObj, DefaultExit):
    """
    Exits are connectors between rooms. Exits are normal Objects except
    they defines the `destination` property. It also does work in the
    following methods:

     basetype_setup() - sets default exit locks (to change, use `at_object_creation` instead).
     at_cmdset_get(**kwargs) - this is called when the cmdset is accessed and should
                              rebuild the Exit cmdset along with a command matching the name
                              of the Exit object. Conventionally, a kwarg `force_init`
                              should force a rebuild of the cmdset, this is triggered
                              by the `@alias` command when aliases are changed.
     at_failed_traverse() - gives a default error message ("You cannot
                            go there") if exit traversal fails and an
                            attribute `err_traverse` is not defined.

    Relevant hooks to overload (compared to other types of Objects):
        at_traverse(traveller, target_loc) - called to do the actual traversal and calling of the other hooks.
                                            If overloading this, consider using super() to use the default
                                            movement implementation (and hook-calling).
        at_after_traverse(traveller, source_loc) - called by at_traverse just after traversing.
        at_failed_traverse(traveller) - called by at_traverse if traversal failed for some reason. Will
                                        not be called if the attribute `err_traverse` is
                                        defined, in which case that will simply be echoed.
    """
    obj_type = "exit"

    def get_room_description(self, looker=None, **kwargs):
        return self.get_display_name(looker=looker, **kwargs)

    def get_dir(self) -> ExitDir:
        if self.db.direction is not None:
            return ExitDir(self.db.direction)
        return ExitDir(-1)

    def at_post_traverse(self, traversing_object, source_location, **kwargs):
        if traversing_object.location and traversing_object.location.obj_type == "room":
            direction = self.get_dir().reverse().name
            traversing_object.location.dgscripts.trigger_enter(direction, traversing_object, **kwargs)

            for obj in traversing_object.location.inventory.all():
                if not obj.obj_type == "character":
                    continue
                if not obj.is_npc():
                    continue
                if obj.can_detect(traversing_object):
                    obj.dgscripts.trigger_greet(direction, traversing_object, **kwargs)
                obj.dgscripts.trigger_greet_all(direction, traversing_object, **kwargs)


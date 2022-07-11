import typing
import operator as o
import re
from collections import defaultdict
from random import randint
from enum import IntEnum, IntFlag
from athanor.exceptions import DGScriptError
from evennia.utils.ansi import strip_ansi
from evennia.utils.utils import lazy_property
from evennia.typeclasses.models import TypeclassBase
from athanor.dgscripts.models import DGScriptDB, DGInstanceDB


class DefaultDGScript(DGScriptDB, metaclass=TypeclassBase):

    @lazy_property
    def instances(self) -> set:
        return set()

    def at_first_save(self):
        pass


class DGType(IntEnum):
    MOB = 0
    ITEM = 1
    ROOM = 2


class MobTriggers(IntFlag):
    EMPTY = 0
    GLOBAL = 1 << 0  # Checked even if Zone empty.
    RANDOM = 1 << 1  # Checked randomly
    COMMAND = 1 << 2  # character types a command
    SPEECH = 1 << 3  # character says word/phrase
    ACT = 1 << 4   # word or phrase received by mob
    DEATH = 1 << 5  # someone dies in room
    GREET = 1 << 6  # someone enters room, and mob sees
    GREET_ALL = 1 << 7  # anything enters room
    ENTRY = 1 << 8   # when mob moves to a new room
    RECEIVE = 1 << 9  # mob receives obj via give
    FIGHT = 1 << 10  # checked each fight pulse
    HITPRCNT = 1 << 11  # fighting and below hp%
    BRIBE = 1 << 12   # mob is given money
    LOAD = 1 << 13  # when mob loads
    MEMORY = 1 << 14  # mob sees a figure it remembers
    CAST = 1 << 15  # mob targetted by spell
    LEAVE = 1 << 16  # someone leaves room, and mob sees
    DOOR = 1 << 17  # a door in the room is manipulated
    TIME = 1 << 19  # trigger fires at certain game time


class ItemTriggers(IntFlag):
    EMPTY = 0
    GLOBAL = 1 << 0  # unused
    RANDOM = 1 << 1  # checked randomly
    COMMAND = 1 << 2 # character types a command
    TIMER = 1 << 5  # object's timer expires
    GET = 1 << 6  # item is picked up with get
    DROP = 1 << 7  # character tries to drop object
    GIVE = 1 << 8  # character tries to give object
    WEAR = 1 << 9  # character tries to wear object
    REMOVE = 1 << 11  # character tries to remove object
    LOAD = 1 << 13  # when object is loaded
    CAST = 1 << 15  # obj targetted by spell
    LEAVE = 1 << 16  # someone leaves room, is seen
    CONSUME = 1 << 18  # when char tries to eat/drink item
    TIME = 1 << 19  # trigger fires at certain game time


class RoomTriggers(IntFlag):
    EMPTY = 0
    GLOBAL = 1 << 0  # check even if zone empty
    RANDOM = 1 << 1  # checked randomly
    COMMAND = 1 << 2  # character types a command
    SPEECH = 1 << 3  # a char says word/phrase
    RESET = 1 << 5  # on zone reset
    ENTER = 1 << 6  # character enters room
    DROP = 1 << 7  # something dropped in room
    CAST = 1 << 15  # spell cast in room
    LEAVE = 1 << 16  # character leaves the room
    DOOR = 1 << 17  # door manipulated in room
    TIME = 1 << 19  # trigger fires at certain game time


class DGState(IntEnum):
    DORMANT = 0
    RUNNING = 1
    WAITING = 2
    ERROR = 3
    DONE = 4
    PURGED = 5


class Nest(IntEnum):
    IF = 0
    WHILE = 1
    SWITCH = 2


def matching_quote(src: str, start: int) -> int:
    try:
        escaped = False
        current = start + 1

        while True:
            if escaped:
                escaped = False
            else:
                match src[current]:
                    case "\\":
                        escaped = True
                    case '"':
                        return current
            current += 1

    except IndexError:
        return -1


def matching_paren(src: str, start: int) -> int:
    try:
        depth = 0
        current = start + 1
        while True:
            match src[current]:
                case "(":
                    depth += 1
                case '"':
                    current = matching_quote(src, current)
                    if current == -1:
                        return -1
                case ")":
                    if depth:
                        depth -= 1
                    else:
                        return current
            current += 1

    except IndexError:
        return -1


def matching_perc(src: str, start: int) -> int:
    try:
        current = start + 1
        while True:
            match src[current]:
                case "(":
                    current = matching_paren(src, current)
                    continue
                case "%":
                    return current
            current += 1
    except IndexError:
        return -1


class DGScriptInstance:

    def __repr__(self):
        return f"<{self.__class__.__name__} on {repr(self.handler.owner)} ({self.proto.id}): {self.proto.key}>"

    def __init__(self, handler, instance: DGInstanceDB):
        self.handler = handler
        self.instance = instance
        self.proto = instance.db_script
        self.state = DGState(instance.db_state)
        self.wait_time = 0.0
        self.curr_line = 0
        self.context = 0
        self.lines: list[str] = list(self.proto.lines)
        self.depth: list[tuple[Nest, int]] = list()
        self.loops = 0
        self.total_loops = 0
        self.vars: dict[str, str] = dict()

    def reset(self):
        self.lines = list(self.proto.lines)
        self.set_state(DGState.DORMANT)
        self.depth.clear()
        self.loops = 0
        self.total_loops = 0
        self.context = 0
        self.vars.clear()

    def script_log(self, msg: str):
        pass

    def set_state(self, state: DGState):
        self.state = state
        self.instance.state = int(state)

    def decrement_timer(self, interval: float):
        self.wait_time -= interval
        if self.wait_time <= 0.0:
            self.wait_time = 0.0
            self.execute()

    def execute(self) -> int:
        try:
            match self.state:
                case DGState.RUNNING | DGState.ERROR | DGState.DONE | DGState.PURGED:
                    raise DGScriptError(f"script called in invalid state {self.state.name}")
            if not len(self.lines):
                raise DGScriptError("script has no lines to execute")
            self.set_state(DGState.RUNNING)
            return self.execute_block(self.curr_line, len(self.lines))
        except DGScriptError as err:
            self.set_state(DGState.ERROR)

            self.script_log(f"{err} - {self.proto.id} - Line {self.curr_line+1}")
            return 0

    def execute_block(self, start: int, end: int) -> int:

        self.curr_line = start

        while self.curr_line < end:

            if self.loops == 50:
                # this has run long enough, let's pause it.
                self.set_state(DGState.WAITING)
                self.wait_time = 1.0
                self.loops = 0
                return 0

            self.loops += 1
            self.total_loops += 1

            if self.total_loops > 2000:
                raise DGScriptError("Runaway Script Halted")

            line = self.get_line(self.curr_line)
            if not line or line.startswith("*"):
                self.curr_line += 1
                continue

            # cover if
            elif line.startswith("if "):
                self.depth.append((Nest.IF, self.curr_line))
                if not self.process_if(line[3:]):
                    self.curr_line = self.find_else_end()
                    continue
            elif line.startswith("elseif "):
                if not self.depth or self.depth[-1][0] != Nest.IF:
                    raise DGScriptError("'elseif' outside of an if block")
                if not self.process_if(line[7:]):
                    self.curr_line = self.find_else_end()
                    continue
            elif line == "else" or line.startswith("else "):
                if not self.depth or self.depth[-1][0] != Nest.IF:
                    raise DGScriptError("'else' outside of an if block")
                continue
            elif line == "end" or line.startswith("end "):
                if not self.depth or self.depth[-1][0] != Nest.IF:
                    raise DGScriptError("'end' outside of an if block")
                self.depth.pop()
                continue

            # cover while
            elif line.startswith("while "):
                self.depth.append((Nest.WHILE, self.curr_line))
                if not self.process_if(line[6:]):
                    self.curr_line = self.find_done()
                    continue

            # cover switch
            elif line.startswith("switch "):
                self.depth.append((Nest.SWITCH, self.curr_line))
                self.curr_line = self.find_case(line[7:])
                continue

            elif line == "break" or line.startswith("break "):
                if not self.depth or self.depth[-1][0] != Nest.SWITCH:
                    raise DGScriptError("'break' outside of a switch-case block")
                self.curr_line = self.find_done()
                continue

            elif line.startswith("case "):
                if not self.depth or self.depth[-1][0] != Nest.SWITCH:
                    raise DGScriptError("'break' outside of a switch-case block")
                # Fall through behavior mimicking C switch
                continue

            elif line == "done" or line.startswith("done "):
                if not self.depth:
                    raise DGScriptError("'done' outside of a switch-case or while block")
                match self.depth[-1][0]:
                    case Nest.SWITCH:
                        # Rewind back to the while clause.
                        self.curr_line = self.depth[-1][1]
                        continue
                    case Nest.WHILE:
                        pass
                    case _:
                        raise DGScriptError("'done' outside of a switch-case or while block")

            else:

                sub_cmd = self.var_subst(line)
                cmd_split = sub_cmd.split(" ", 1)
                cmd = cmd_split[0]

                match cmd:
                    case "nop":
                        # Do nothing.
                        pass
                    case "return":
                        pass
                    case "wait":
                        pass
                    case _:
                        if (func := getattr(self, f"cmd_{cmd}", None)):
                            func(*cmd_split)
                        else:
                            self.handler.owner.execute_cmd(sub_cmd)

            self.curr_line += 1


    def truthy(self, value: str) -> bool:
        if not value:
            return False
        return value != "0"

    def process_if(self, cond: str) -> bool:
        return self.truthy(self.eval_expr(cond).strip())

    def eval_expr(self, line: str) -> str:
        trimmed = strip_ansi(line.strip())

        if (result := self.eval_lhs_op_rhs(trimmed)):
            return result
        elif trimmed.startswith("("):
            m = matching_paren(trimmed, 0)
            if m != 1:
                return self.eval_expr(trimmed[1:m-1])
        else:
            return self.var_subst(trimmed)

    ops_map = {
        "||": o.or_,
        "&&": o.and_,
        "==": o.eq,
        "!=": o.ne,
        "<=": o.le,
        ">=": o.ge,
        "<": o.lt,
        ">": o.gt,
        "/=": o.truediv,
        "-": o.sub,
        "+": o.add,
        "/": o.floordiv,
        "*": o.mul,
        "!": o.not_
    }

    def eval_lhs_op_rhs(self, expr: str) -> typing.Optional[str]:

        for op in self.ops_map.keys():
            try:
                lhs, rhs = expr.split(op, 1)
                lhr = self.eval_expr(lhs)
                rhr = self.eval_expr(rhs)
                return self.eval_op(op, lhr, rhr)
            except ValueError:
                continue

    def eval_op(self, op: str, lhs: str, rhs: str) -> str:
        op_found = self.ops_map[op]
        if lhs.isnumeric() and rhs.isnumeric():
            a = int(lhs)
            b = int(rhs)
            return str(op_found(a, b))
        else:
            match op:
                case "&&":
                    return str(int(self.truthy(lhs) and self.truthy(rhs)))
                case "==" | "!=":
                    return str(int(op_found(lhs, rhs)))
                case "||":
                    return str(int(self.truthy(lhs) or self.truthy(rhs)))
                case _:
                    return "0"



    def find_replacement(self, v: str) -> str:
        pass

    def add_local_var(self, name: str, value: str):
        pass

    def get_line(self, i: int) -> str:
        return self.lines[i].lower().trim()

    def find_else_end(self, match_elseif: bool = True, match_else: bool = True) -> int:
        if not self.depth or self.depth[-1][0] != Nest.IF:
            raise DGScriptError("find_end called outside of if! alert a codewiz!")

        i = self.depth[-1][1]
        total = len(self.lines)
        while i < total:
            line = self.get_line(i)
            if not line or line.startswith("*"):
                pass

            elif match_elseif and line.startswith("elseif "):
                return i

            elif match_else and (line.startswith("else ") or line.startswith("else")):
                return i

            elif line.startswith("end"):
                return i

            elif line.startswith("if "):
                self.depth.append((Nest.IF, i))
                i = self.find_done()
                self.depth.pop()

            elif line.startswith("switch "):
                self.depth.append((Nest.SWITCH, i))
                i = self.find_done()
                self.depth.pop()

            elif line.startswith("while "):
                self.depth.append((Nest.WHILE, i))
                i = self.find_done()
                self.depth.pop()

            elif line == "default" or line.startswith("default "):
                raise DGScriptError("'default' outside of a switch-case block")

            elif line == "done" or line.startswith("done "):
                raise DGScriptError("'done' outside of a switch-case or while block")

            elif line == "case" or line.startswith("case "):
                raise DGScriptError("'case' outside of a switch-case block")

            i += 1

        raise DGScriptError("'if' without corresponding end")


    def find_end(self) -> int:
        return self.find_else_end(match_elseif=False, match_else=False)

    def find_done(self) -> int:
        if not self.depth or self.depth[-1][0] not in (Nest.SWITCH, Nest.WHILE):
            raise DGScriptError("find_done called outside of a switch-case or while block! alert a codewiz!")

        inside = self.depth[-1][0].name.capitalize()

        i = self.depth[-1][1]
        total = len(self.lines)
        while i < total:
            line = self.get_line(i)
            if not line or line.startswith("*"):
                pass

            elif line.startswith("if "):
                self.depth.append((Nest.IF, i))
                i = self.find_done()
                self.depth.pop()

            elif line.startswith("switch "):
                self.depth.append((Nest.SWITCH, i))
                i = self.find_done()
                self.depth.pop()

            elif line.startswith("while "):
                self.depth.append((Nest.WHILE, i))
                i = self.find_done()
                self.depth.pop()

            elif line.startswith("elseif "):
                raise DGScriptError("'elseif' outside of an if block")

            elif line.startswith("else ") or line == "else":
                raise DGScriptError("'else' outside of an if block")

            elif line == "end" or line.startswith("end "):
                raise DGScriptError("'end' outside of an if block")

            elif line == "default" or line.startswith("default "):
                raise DGScriptError("'default' outside of a switch-case block")

            elif line == "done" or line.startswith("done "):
                return i

            i += 1
        raise DGScriptError(f"'{inside}' without corresponding done")

    def find_case(self, cond: str) -> int:
        if not self.depth or self.depth[-1][0] != Nest.SWITCH:
            raise DGScriptError("find_case called outside of if! alert a codewiz!")

        res = self.eval_expr(cond)

        i = self.depth[-1][1]
        total = len(self.lines)
        while i < total:
            line = self.get_line(i)
            if not line or line.startswith("*"):
                pass

            if line.startswith("case ") and self.truthy(self.eval_op("==", res, line[5:])):
                return i

            elif line == "default" or line.startswith("default "):
                return i

            elif line.startswith("end"):
                return i

            elif line.startswith("if "):
                self.depth.append((Nest.IF, i))
                i = self.find_done()
                self.depth.pop()

            elif line.startswith("switch "):
                self.depth.append((Nest.SWITCH, i))
                i = self.find_done()
                self.depth.pop()

            elif line.startswith("while "):
                self.depth.append((Nest.WHILE, i))
                i = self.find_done()
                self.depth.pop()

            elif line.startswith("elseif "):
                raise DGScriptError("'elseif' outside of an if block")

            elif line.startswith("else ") or line == "else":
                raise DGScriptError("'else' outside of an if block")

            i += 1

        raise DGScriptError("'if' without corresponding end")

    _re_expr = re.compile(r"^(?P<everything>(?P<var>\w+)(?:.(?P<field>\w+?)?)?(?P<call>\((?P<arg>[\w| ]+)?\))?)$")

    def eval_var(self, varname: str, field: str, call: str, arg: str) -> str:
        pass

    def get_var(self, varname: str, context: int = -1) -> typing.Optional[str]:
        pass

    def var_subst(self, line: str) -> str:
        pass

    def process_eval(self, cmd: str):
        args = cmd.split(" ", 2)

        if len(args) != 3:
            self.script_log(f"eval w/o an arg: {cmd}")
            return

        self.vars[args[1]] = self.eval_expr(args[2])

    def extract_value(self, cmd: str):
        pass

    def dg_letter_value(self, cmd: str):
        pass

    def makeuid_var(self, cmd: str):
        pass

    def do_dg_cast(self, cmd: str):
        pass

    def do_dg_affect(self, cmd: str):
        pass

    def process_global(self, cmd: str):
        pass

    def process_context(self, cmd: str):
        pass

    def process_rdelete(self, cmd: str):
        pass

    def process_return(self, cmd: str) -> int:
        pass

    def process_set(self, cmd: str):
        args = cmd.split(" ")
        if len(args) != 3:
            self.script_log(f"set with improper arg: {cmd}")
            return
        self.vars[args[1]] = args[2]

    def process_unset(self, cmd: str):
        args = cmd.split(" ")
        if len(args) != 2:
            self.script_log(f"unset with improper arg: {cmd}")
            return
        self.vars.pop(args[1], None)

    def process_wait(self, cmd: str):
        pass

    def process_detach(self, cmd: str):
        pass

    def process_attach(self, cmd: str):
        pass


class DGHandler:
    """
    Handler that's meant to be attached to an Athanor Object.

    This one is Abstract, don't use it directly!
    """
    attr_name = "triggers"

    def __init__(self, owner):
        self.owner = owner
        self.scripts: dict[int, DGScriptInstance] = dict()
        self.vars: dict[int, dict[str, str]] = defaultdict(dict)
        self.load()

    def load(self):
        for i in self.owner.dg_scripts.all():
            self.scripts[i.script.id] = DGScriptInstance(self, i)
        if not self.scripts:
            if self.owner.db.triggers:
                for i in self.owner.db.triggers:
                    self.attach(i)
                del self.owner.db.triggers

    def ids(self):
        return self.scripts.keys()

    def all(self):
        return self.scripts.values()

    def attach(self, script_id):
        if (dg := DefaultDGScript.objects.filter(id=script_id).first()):
            new_dg, created = self.owner.dg_scripts.get_or_create(db_script=dg)
            if created:
                new_dg.save()
            self.scripts[dg.id] = DGScriptInstance(self, new_dg)

    def detach(self, script_id):
        if (script := self.scripts.pop(script_id, None)):
            self.owner.dg_scripts.filter(db_script=script.proto).delete()

    def get_ready(self, trig_type):
        ready = list()
        for v in self.all():
            if v.state == DGState.DORMANT and v.proto.db_trigger_type & trig_type:
                ready.append(v)
        return ready

    def reset_finished(self):
        for k, v in self.scripts.items():
            if v.state > 2:
                v.reset()

    def trigger_random(self):
        pass

    def trigger_given(self, giver, getter, **kwargs):
        pass

    def trigger_gave_item(self, item, getter, **kwargs):
        pass

    def trigger_gifted_item(self, item, giver, **kwargs):
        pass

    def trigger_speech(self, speech, speaker, **kwargs):
        pass

    def trigger_act(self, action, actor, **kwargs):
        pass

    def trigger_drop(self, item, dropper, **kwargs):
        pass

    def trigger_enter(self, direction, traveler, **kwargs):
        pass

    def trigger_greet(self, direction, traveler, **kwargs):
        pass

    def trigger_greet_all(self, direction, traveler, **kwargs):
        pass


class DGMobHandler(DGHandler):
    dg_type = DGType.MOB

    def trigger_greet(self, direction, traveler, **kwargs):
        for v in self.get_ready(MobTriggers.GREET):
            if randint(1, 100) <= v.proto.db_narg:
                v.vars["direction"] = direction
                v.vars["actor"] = traveler
                v.execute()


class DGItemHandler(DGHandler):
    dg_type = DGType.ITEM


class DGRoomHandler(DGHandler):
    dg_type = DGType.ROOM


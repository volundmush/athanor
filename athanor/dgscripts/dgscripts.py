import typing
import operator as o
import re
from django.conf import settings
from collections import defaultdict
from random import randint
from enum import IntEnum, IntFlag
from athanor.exceptions import DGScriptError
from evennia.utils.ansi import strip_ansi
from evennia.utils.utils import lazy_property, class_from_module, logger
from evennia.typeclasses.models import TypeclassBase
from evennia import ObjectDB
from athanor.dgscripts.models import DGScriptDB, DGInstanceDB
from athanor import DG_INSTANCE_CLASSES, DG_FUNCTIONS, DG_VARS
from athanor.commands.base import Command


class DefaultDGScript(DGScriptDB, metaclass=TypeclassBase):

    @lazy_property
    def instances(self) -> set:
        return set()

    def at_first_save(self):
        pass


class DGType(IntEnum):
    CHARACTER = 0
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
        return f"<{self.state.name} {self.__class__.__name__} on {repr(self.handler.owner)} ({self.proto.id}): {self.proto.key}>"

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
        self.curr_line = 0
        self.lines = list(self.proto.lines)
        self.set_state(DGState.DORMANT)
        self.depth.clear()
        self.loops = 0
        self.total_loops = 0
        self.context = 0
        self.vars.clear()

    def script_log(self, msg: str):
        print(f"SCRIPT ERROR: {msg}")

    def set_state(self, state: DGState):
        self.state = state
        self.instance.state = int(state)
        print(f"{self} STATE: {self.state.name}")

    def decrement_timer(self, interval: float):
        self.wait_time -= interval
        if self.wait_time <= 0.0:
            self.wait_time = 0.0
            self.execute()

    def execute(self) -> int:
        print(f"EXECUTE: {self}")
        try:
            match self.state:
                case DGState.RUNNING | DGState.ERROR | DGState.DONE | DGState.PURGED:
                    raise DGScriptError(f"script called in invalid state {self.state.name}")
            if not len(self.lines):
                raise DGScriptError("script has no lines to execute")
            self.set_state(DGState.RUNNING)
            results = self.execute_block(self.curr_line, len(self.lines))
            if self.state == DGState.DONE:
                self.reset()
            return results
        except DGScriptError as err:
            self.set_state(DGState.ERROR)
            self.script_log(f"{err} - {self.proto.id} - Line {self.curr_line+1}")
            return 0

    def execute_block(self, start: int, end: int) -> int:

        ret_val = 1

        self.curr_line = start

        while self.curr_line < end:
            print(f"CURR_LINE: {self.curr_line} against {end}")

            if self.loops == 500:
                print(f"{self} RAN TOO LONG!")
                # this has run long enough, let's pause it.
                self.set_state(DGState.WAITING)
                self.wait_time = 1.0
                self.loops = 0
                return ret_val

            self.loops += 1
            self.total_loops += 1

            if self.total_loops > 2000:
                raise DGScriptError("Runaway Script Halted")

            line = self.get_line(self.curr_line)
            if not line or line.startswith("*"):
                print(f"GOT COMMENT... skipping...")

            # cover if
            elif line.startswith("if "):
                self.depth.append((Nest.IF, self.curr_line))
                print(f"CHECKING IF: {line}")
                if not self.process_if(line[3:]):
                    print(f"IF {line} failed, checking for else/end...")
                    self.curr_line = self.find_else_end()
                    print(f"IF Failed, proceeding at {self.curr_line}")
                    continue
            elif line.startswith("elseif "):
                if not self.depth or self.depth[-1][0] != Nest.IF:
                    raise DGScriptError("'elseif' outside of an if block")
                self.curr_line = self.find_end()
                continue
            elif line == "else" or line.startswith("else "):
                if not self.depth or self.depth[-1][0] != Nest.IF:
                    raise DGScriptError("'else' outside of an if block")
                self.curr_line = self.find_end()
                continue
            elif line == "end" or line.startswith("end "):
                if not self.depth or self.depth[-1][0] != Nest.IF:
                    raise DGScriptError("'end' outside of an if block")
                self.depth.pop()
                print(f"END OF IF {self.curr_line}")

            # cover while
            elif line.startswith("while "):
                self.depth.append((Nest.WHILE, self.curr_line))
                if not self.process_if(line[6:]):
                    print(f"WHILE {line} IS TRUE")
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
                    case Nest.WHILE:
                        # Rewind back to the while clause.
                        print(f"REACHED WHILE END {self.curr_line}")
                        self.curr_line = self.depth[-1][1]
                        self.depth.pop()
                        continue
                    case Nest.SWITCH:
                        print(f"REACHED SWITCH END {self.curr_line}")
                        self.depth.pop()
                    case _:
                        raise DGScriptError("'done' outside of a switch-case or while block")


            else:
                print(f"Checking Line... {line}")
                sub_cmd = self.var_subst(line)
                print(f"post var_subst: {sub_cmd}")
                cmd_split = sub_cmd.split(" ", 1)
                cmd = cmd_split[0]

                match cmd.lower():
                    case "nop":
                        # Do nothing.
                        pass
                    case "return":
                        if len(cmd_split) > 1:
                            out = cmd_split[1]
                            self.set_state(DgState.DONE)
                            if out not in ("0", "1"):
                                return int(self.truthy(out))
                            else:
                                return int(out)
                        else:
                            return ret_val
                    case "wait":
                        if (wait_time := self.cmd_wait(sub_cmd)):
                            self.set_state(DGState.WAITING)
                            self.wait_time = wait_time
                            self.loops = 0
                            self.curr_line += 1
                            return ret_val
                    case _:
                        if (func := getattr(self, f"cmd_{cmd}", None)):
                            func(sub_cmd)
                        else:
                            print(f"Unrecognized command {cmd}, passing to execute_cmd...")
                            self.handler.owner.execute_cmd(sub_cmd)

            print(f"Incrementing line...")
            self.curr_line += 1

        self.set_state(DGState.DONE)

    def truthy(self, value: str) -> bool:
        if not value:
            print(f"TRUTHY OF {value}: False")
            return False
        res = value != "0"
        print(f"TRUTHY of {value}: {res}")
        return res

    def process_if(self, cond: str) -> bool:
        result = self.truthy(self.maybe_negate(self.eval_expr(cond).strip()))
        print(f"IF {cond} : {result}")
        return result

    def eval_expr(self, line: str) -> str:
        print(f"EVAL_EXPR: {line}")
        trimmed = line.strip()
        if trimmed.startswith("("):
            m = matching_paren(trimmed, 0)
            if m != -1:
                return self.eval_expr(trimmed[1:m])
        elif (result := self.eval_lhs_op_rhs(trimmed)):
            return result
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
        #"!": o.not_
    }

    def eval_lhs_op_rhs(self, expr: str) -> typing.Optional[str]:
        print(f"EVAL_LHS_OP_RHS: {expr}")
        for op in self.ops_map.keys():
            try:
                lhs, rhs = expr.split(op, 1)
                lhs = lhs.strip()
                rhs = rhs.strip()
                print(f"LHS: {lhs}, RHS: {rhs}")
                lhr = self.eval_expr(lhs)
                rhr = self.eval_expr(rhs)
                print(f"LHR: {lhr}, RHR: {rhr}")
                result = self.eval_op(op, lhr, rhr)
                print(f"EVAL OP RESULT: {result}")
                return result
            except ValueError:
                continue

    def maybe_negate(self, data: str):
        if data.startswith("!"):
            return "0" if self.truthy(self.maybe_negate(data[1:])) else "1"
        return data

    def eval_op(self, op: str, lhs: str, rhs: str) -> str:
        op_found = self.ops_map[op]
        print(f"EVAL OP: {op} - {op_found}")
        result = "0"

        lhs = self.maybe_negate(lhs)
        rhs = self.maybe_negate(rhs)

        if lhs.isnumeric() and rhs.isnumeric():
            a = int(lhs)
            b = int(rhs)
            if op_found(a, b):
                result = "1"
        else:
            match op:
                case "&&":
                    if self.truthy(lhs) and self.truthy(rhs):
                        result = "1"
                case "==" | "!=":
                    if op_found(lhs.lower(), rhs.lower()):
                        result = "1"
                case "||":
                    if  self.truthy(lhs) or self.truthy(rhs):
                        result = "1"
                case _:
                    result = "0"
        return result

    def find_replacement(self, v: str) -> str:
        pass

    def add_local_var(self, name: str, value: str):
        pass

    def get_line(self, i: int) -> str:
        line = self.lines[i].strip()
        print(f"GET_LINE: {line}")
        return line

    def find_else_end(self, match_elseif: bool = True, match_else: bool = True) -> int:
        if not self.depth or self.depth[-1][0] != Nest.IF:
            print(f"FIND ELSE END WHOOPS 1")
            raise DGScriptError("find_end called outside of if! alert a codewiz!")

        i = self.depth[-1][1] + 1
        total = len(self.lines)
        while i < total:
            line = self.get_line(i)
            print(f"Scanning for Else {match_else}, Elseif {match_elseif}, line {i} : {line}")
            if not line or line.startswith("*"):
                pass

            elif match_elseif and line.startswith("elseif ") and self.process_if(line[7:]):
                print(f"found truthy elseif {i}")
                return i + 1

            elif match_else and (line.startswith("else ") or line == "else"):
                print(f"found else {i}")
                return i + 1

            elif line.startswith("end ") or line == "end":
                print(f"found end {i}")
                return i

            elif line.startswith("if "):
                depth = len(self.depth)
                print(f"Nested IF detected at {i}. Depth: {depth}")
                self.depth.append((Nest.IF, i))
                i = self.find_end() + 1
                print(f"exited depth {depth} IF...")
                self.depth.pop()
                continue

            elif line.startswith("switch "):
                self.depth.append((Nest.SWITCH, i))
                i = self.find_done() + 1
                self.depth.pop()
                continue

            elif line.startswith("while "):
                self.depth.append((Nest.WHILE, i))
                i = self.find_done() + 1
                self.depth.pop()
                continue

            elif line == "default" or line.startswith("default "):
                raise DGScriptError("'default' outside of a switch-case block")

            elif line == "done" or line.startswith("done "):
                raise DGScriptError("'done' outside of a switch-case or while block")

            elif line == "case" or line.startswith("case "):
                raise DGScriptError("'case' outside of a switch-case block")

            print(f"incrementing {i}")
            i += 1

        raise DGScriptError("'if' without corresponding end")


    def find_end(self) -> int:
        return self.find_else_end(match_elseif=False, match_else=False)

    def find_done(self) -> int:
        if not self.depth or self.depth[-1][0] not in (Nest.SWITCH, Nest.WHILE):
            raise DGScriptError("find_done called outside of a switch-case or while block! alert a codewiz!")

        inside = self.depth[-1][0].name.capitalize()

        i = self.depth[-1][1] + 1
        total = len(self.lines)
        while i < total:
            line = self.get_line(i)
            if not line or line.startswith("*"):
                pass

            elif line.startswith("if "):
                self.depth.append((Nest.IF, i))
                i = self.find_end() + 1
                self.depth.pop()
                continue

            elif line.startswith("switch "):
                self.depth.append((Nest.SWITCH, i))
                i = self.find_done() + 1
                self.depth.pop()
                continue

            elif line.startswith("while "):
                self.depth.append((Nest.WHILE, i))
                i = self.find_done() + 1
                self.depth.pop()
                continue

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

        i = self.depth[-1][1] + 1
        total = len(self.lines)
        while i < total:
            line = self.get_line(i)
            if not line or line.startswith("*"):
                pass

            if line.startswith("case ") and self.truthy(self.eval_op("==", res, line[5:])):
                return i + 1

            elif line == "default" or line.startswith("default "):
                return i + 1

            elif line == "done" or line.startswith("done "):
                return i

            elif line.startswith("if "):
                self.depth.append((Nest.IF, i))
                i = self.find_end() + 1
                self.depth.pop()
                continue

            elif line.startswith("switch "):
                self.depth.append((Nest.SWITCH, i))
                i = self.find_done() + 1
                self.depth.pop()
                continue

            elif line.startswith("while "):
                self.depth.append((Nest.WHILE, i))
                i = self.find_done() + 1
                self.depth.pop()
                continue

            elif line.startswith("end ") or line == "end":
                raise DGScriptError("'end' outside of an if block")

            elif line.startswith("elseif "):
                raise DGScriptError("'elseif' outside of an if block")

            elif line.startswith("else ") or line == "else":
                raise DGScriptError("'else' outside of an if block")

            i += 1

        raise DGScriptError("'switch' without corresponding done")

    _re_expr = re.compile(r"^(?P<everything>(?P<varname>\w+)(?:.(?P<field>\w+?)?)?(?P<call>\((?P<arg>[\w| ]+)?\))?)$")

    _re_dbref = re.compile(r"^#\d+$")

    def get_members(self, data: str):
        start = 0
        i = 0
        member = ""
        call = False
        arg = ""
        try:
            while True:
                match data[i]:
                    case ".":
                        yield {"member": member, "call": call, "arg": arg}
                        member = ""
                        call = False
                        arg = ""
                    case "(":
                        m = matching_paren(data, i)
                        if m != -1:
                            arg = data[i+1:m]
                            call = True
                            i = m + 1
                            continue
                    case _:
                        if call:
                            pass
                        else:
                            member += data[i]
                i += 1

        except IndexError as err:
            yield {"member": member, "call": call, "arg": arg}

    def eval_var(self, data: str) -> str:

        def _db_check(text):
            if hasattr(text, "dbref"):
                return text
            if self._re_dbref.match(text):
                if (found := ObjectDB.objects.filter(id=int(text[1:])).first()):
                    return found
            return text

        last_mem = None
        for mem in self.get_members(data):
            if hasattr(last_mem, "dbref"):
                result = last_mem.dgscripts.evaluate(self, **mem)
                last_mem = _db_check(result)
            elif callable(last_mem):
                result = last_mem(self, **mem)
                last_mem = _db_check(result)
                last_mem = result
            elif isinstance(last_mem, str):
                # strings CANNOT have members.
                return ""
            elif last_mem is not None:
                # safety check
                return ""
            else:
                # this is probably a special var. Let's check those first.
                if (found := DG_VARS.get(mem["member"].lower(), None)):
                    if callable(found):
                        last_mem = found
                    elif isinstance(found, str):
                        last_mem = _db_check(found)
                        last_mem = found
                else:
                    v = self.vars.get(mem["member"].lower(), "")
                    last_mem = _db_check(v)

        while callable(last_mem):
            last_mem = last_mem(self)

        if not isinstance(last_mem, str):
            return ""
        return last_mem


        if self._re_dbref.match(varname):
            # this is a dbref. we should look it up.
            if (found := ObjectDB.objects.filter(id=int(varname[1:])).first()):
                return found.dgscripts.evaluate(self, varname, field, call, arg)
            return ""

        if (func := getattr(self, f"eval_var_{varname}", None)):
            return func(varname, field, call, arg)

        var = self.vars.get(varname, "")

        if isinstance(var, str):
            if self._re_dbref.match(var):
                # variable contains a dbref. look it up.
                if (found := ObjectDB.objects.filter(id=int(var[1:])).first()):
                    return found.dgscripts.evaluate(self, varname, field, call, arg)
                return ""
            return var
        else:
            # if it's not a string but it exists, it -has- to be an actor.
            return var.dgscripts.evaluate(self, varname, field, call, arg)


    def get_var(self, varname: str, context: int = -1) -> typing.Optional[str]:
        pass

    def var_subst(self, line: str) -> str:
        print(f"VAR_SUBST: {line}")
        out = ""
        i = 0
        escaped = False

        try:
            while True:
                if escaped:
                    i += 1
                    escaped = False
                    continue

                match line[i]:
                    case "\\":
                        escaped = True
                    case "%":
                        m = matching_perc(line, i)
                        if m != -1:
                            # we now have a sub-section. But there might be more %-sections!
                            # so, we recurse...
                            recursed = self.var_subst(line[i+1:m])
                            # now confident that all nested variables are evaluated...
                            out += self.eval_var(recursed)
                            i = m + 1
                            continue
                    case _:
                        out += line[i]

                i += 1

        except IndexError:
            return out

    def process_eval(self, cmd: str):
        args = cmd.split(" ", 2)

        if len(args) != 3:
            self.script_log(f"eval w/o an arg: {args}")
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

    def cmd_global(self, cmd: str):
        pass

    def cmd_context(self, cmd: str):
        pass

    def cmd_rdelete(self, cmd: str):
        args = cmd.split()
        if len(args) < 2:
            self.script_log(f"rdelete with improper arg: {cmd}")
            return
        if args[1] not in self.vars:
            self.script_log(f"rdelete missing target var: {cmd}")
            return
        if not (target := self.handler.owner.search(args[2], use_dbref=True)):
            self.script_log(f"rdelete target not found: {cmd}")
            return
        target.dgscripts.vars
        target.dgscripts.vars[self.context].pop(args[1])
        target.dgscripts.save()

    def cmd_remote(self, cmd: str):
        args = cmd.split()
        if len(args) < 2:
            self.script_log(f"remote with improper arg: {cmd}")
            return
        if args[1] not in self.vars:
            self.script_log(f"remote missing local var: {cmd}")
            return
        if not (target := self.handler.owner.search(args[2], use_dbref=True)):
            self.script_log(f"remote target not found: {cmd}")
            return
        target.dgscripts.vars[self.context][args[1]] = self.vars[args[1]]
        target.dgscripts.save()

    def cmd_set(self, cmd: str):
        args = cmd.split()
        if len(args) < 2:
            self.script_log(f"set with improper arg: {cmd}")
            return
        if len(args) < 3:
            args.append("")
        self.vars[args[1]] = args[2]

    def cmd_unset(self, cmd: str):
        args = cmd.split()
        if len(args) != 2:
            self.script_log(f"unset with improper arg: {cmd}")
            return
        self.vars.pop(args[1], None)

    def cmd_wait(self, cmd: str):
        args = cmd.split()
        if len(args) < 2:
            args.append("1")

        if not args[1].isnumeric():
            self.script_log(f"wait with improper arg: {args}")
            return 0

        if len(args) < 3:
            args.append("s")

        match args[2].lower():
            case "s" | "sec" | "second" | "seconds":
                return float(args[1])
            case _:
                return float(args[1])


    def cmd_detach(self, cmd: str):
        pass

    def cmd_attach(self, cmd: str):
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
            self.scripts[i.script.id] = DG_INSTANCE_CLASSES[DGType(i.script.attach_type).name.lower()](self, i)
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
            self.scripts[dg.id] = DG_INSTANCE_CLASSES[DGType(dg.attach_type).name.lower()](self, new_dg)

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

    def reset_active(self):
        for k, v in self.scripts.items():
            if v.state > 0:
                v.reset()

    def resume(self):
        for k, v in self.scripts.items():
            if v.state == DGState.WAITING:
                v.execute()

    def trigger_random(self):
        for s in self.get_ready(MobTriggers.RANDOM):
            if randint(1, 100) <= s.proto.narg:
                s.execute()

    def trigger_given(self, giver, getter, **kwargs):
        pass

    def trigger_gave_item(self, item, getter, **kwargs):
        pass

    def trigger_gifted_item(self, item, giver, **kwargs):
        pass

    def trigger_speech(self, speech, speaker, **kwargs):
        for s in self.get_ready(MobTriggers.SPEECH):
            s.vars["actor"] = speaker
            s.vars["speech"] = speech
            s.execute()

    def trigger_act(self, action, actor, **kwargs):
        pass

    def trigger_drop(self, item, dropper, **kwargs):
        for v in self.get_ready(RoomTriggers.ENTER):
            if randint(1, 100) <= v.proto.db_narg:
                v.vars["object"] = item
                v.vars["actor"] = dropper
                return v.execute()
        return True

    def trigger_enter(self, direction, traveler, **kwargs):
        for v in self.get_ready(RoomTriggers.ENTER):
            if randint(1, 100) <= v.proto.db_narg:
                v.vars["direction"] = direction
                v.vars["actor"] = traveler
                v.execute()

    def trigger_greet(self, direction, traveler, **kwargs):
        for v in self.get_ready(MobTriggers.GREET):
            if randint(1, 100) <= v.proto.db_narg:
                v.vars["direction"] = direction
                v.vars["actor"] = traveler
                v.execute()

    def trigger_greet_all(self, direction, traveler, **kwargs):
        for v in self.get_ready(MobTriggers.GREET_ALL):
            v.vars["direction"] = direction
            v.vars["actor"] = traveler
            v.execute()

    def trigger_zreset(self):
        for v in self.get_ready(RoomTriggers.RESET):
            v.execute()

    def evaluate(self, script: DGScriptInstance, member: str = "", call: bool = False, arg: str = "") -> str:
        if (func := DG_FUNCTIONS[self.owner.obj_type].get(member.lower(), None)):
            return func(self.owner, script, arg if call else None)
        return self.vars[script.context].get(member.lower(), "")


class DGScriptItemInstance(DGScriptInstance):
    pass


class DGScriptCharacterInstance(DGScriptInstance):
    pass


class DGScriptRoomInstance(DGScriptInstance):
    pass


class DGMobHandler(DGHandler):
    dg_type = DGType.CHARACTER



class DGItemHandler(DGHandler):
    dg_type = DGType.ITEM


class DGRoomHandler(DGHandler):
    dg_type = DGType.ROOM


def stat_get_set(obj, script, field, handler, arg: str) -> str:
    """
    Util function to make writing dgfuncs easier.
    """
    if arg:
        try:
            getattr(obj, handler).mod(int(arg))
        except (ValueError, TypeError):
            script.script_log(f"invalid arg for {field}: {arg}")
    return str(getattr(obj, handler).effective())


class DGCommand(Command):

    def func(self):
        if (found := self.obj.dgscripts.scripts.get(self.script_id, None)):
            if found.state == DGState.DORMANT:
                found.vars["actor"] = self.caller
                found.vars["arg"] = self.args.strip()
                found.vars["cmd"] = self.cmdstring
                found.execute()

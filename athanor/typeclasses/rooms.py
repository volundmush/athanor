import typing
from collections import defaultdict
from .mixin import AthanorBase
from evennia.objects.objects import DefaultRoom, DefaultObject
from athanor.mudrich import EvToRich, MudText
from rich.console import Group, group
from rich.table import Table
from evennia.utils.ansi import ANSIString
from django.conf import settings
from rich.style import NULL_STYLE

class AthanorRoom(DefaultRoom, AthanorBase):
    """
    Not much different from Evennia DefaultRooms.
    """
    _content_types = ("room",)
    compass_template = """||{N:^3}||
||{NW:>3}|| ||{U:^3}|| ||{NE:<3}||
||{W:>3}|| ||{I:^3}|| ||{E:<3}||
||{SW:>3}|| ||{D:^3}|| ||{SE:<3}||
||{S:^3}||
"""

    def at_object_creation(self):
        # typing.Dict[ExitDir, "AthanorExit"]
        self.db.exit_grid = dict()

    def at_pre_move(self, destination: typing.Optional[DefaultObject], **kwargs):
        """
        Called just before moving object to destination.
        If returns False, move is cancelled.
        """
        if not destination:
            return False
        return "structure" in destination._content_types

    def at_object_receive(self, obj: DefaultObject, source_location: typing.Optional[DefaultObject], move_type="move", **kwargs):
        """
        Called after an object has been moved into this object.

        Anything inside a Room is simply there.
        """
        del obj.db.coordinates
        if "exit" in obj._content_types:
            if obj.db.direction:
                self.db.exit_grid[obj.db.direction] = obj

    def generate_map_icon(self, looker):
        return "o"

    def generate_automap(self, looker, min_y=-2, max_y=2, min_x=-2, max_x=2):
        visited = set()

        cur_map = defaultdict(lambda: defaultdict(lambda: " "))

        def scan(room, cur_x, cur_y):
            if room in visited:
                return
            visited.add(room)
            cur_map[cur_y][cur_x] = room.generate_map_icon(looker)

            con_map = room.get_visible_contents(looker)
            for ex_obj in con_map["exits"]:
                if not ex_obj.destination:
                    continue

                match ex_obj.key:
                    case "north":
                        if (cur_y + 1) <= max_y:
                            scan(ex_obj.destination, cur_x, cur_y + 1)
                    case "south":
                        if (cur_y - 1) >= min_y:
                            scan(ex_obj.destination, cur_x, cur_y - 1)
                    case "east":
                        if (cur_x + 1) <= max_x:
                            scan(ex_obj.destination, cur_x + 1, cur_y)
                    case "west":
                        if (cur_x - 1) >= min_x:
                            scan(ex_obj.destination, cur_x - 1, cur_y)
                    case "northeast":
                        if ((cur_y + 1) <= max_y) and ((cur_x + 1) <= max_x):
                            scan(ex_obj.destination, cur_x + 1, cur_y + 1)
                    case "northwest":
                        if ((cur_y + 1) <= max_y) and ((cur_x - 1) >= min_x):
                            scan(ex_obj.destination, cur_x - 1, cur_y + 1)
                    case "southeast":
                        if ((cur_y - 1) >= min_y) and ((cur_x + 1) <= max_x):
                            scan(ex_obj.destination, cur_x + 1, cur_y - 1)
                    case "southwest":
                        if ((cur_y - 1) >= min_y) and ((cur_x - 1) >= min_x):
                            scan(ex_obj.destination, cur_x - 1, cur_y - 1)

        scan(self, 0, 0)

        cur_map[0][0] = "|rX|n"

        return cur_map

    def generate_compass(self, looker):
        con_map = self.get_visible_contents(looker)
        compass_dict = defaultdict(str)

        for ex in con_map["exits"]:
            upper = ex.key.upper()
            match ex.key:
                case "north" | "south":
                    compass_dict[upper[0]] = f" |c{upper[0]}|n "
                case "up" | "down":
                    compass_dict[upper[0]] = f" |y{upper[0]}|n "
                case "east":
                    compass_dict["E"] = "|cE|n  "
                case "west":
                    compass_dict["W"] = "  |cW|n"
                case "northwest" | "southwest":
                    compass_dict[upper[0] + upper[5]] = f" |c{upper[0] + upper[5]}|n"
                case "northeast" | "southeast":
                    compass_dict[upper[0] + upper[5]] = f"|c{upper[0] + upper[5]}|n "
                case "inside":
                    compass_dict["I"] = f" |MI|n "
                case "outside":
                    compass_dict["I"] = "|MOUT|n"

        return self.compass_template.format_map(compass_dict)

    def generate_map_legend(self, looker, **kwargs):
        return ""

    def generate_builder_info(self, looker, **kwargs):
        return ""

    header_line = MudText("O----------------------------------------------------------------------O")
    subheader_line = MudText("------------------------------------------------------------------------")

    @group()
    def render_automap(self, looker, **kwargs):
        yield self.subheader_line
        y_coor = [2, 1, 0, -1, -2]
        x_coor = [-4, -3, -2, -1, 0, 1, 2, 3, 4]
        automap = self.generate_automap(looker, min_x=-4, max_x=4)
        col_automap = EvToRich("\r\n".join(["".join([automap[y][x] for x in x_coor]) for y in y_coor]))
        map_legend = self.generate_map_legend(looker, **kwargs)
        table = Table(box=None)
        table.add_column("Compass", width=17, header_style=NULL_STYLE, justify="center")
        table.add_column("Auto-Map", width=10, header_style=NULL_STYLE)
        table.add_column("Map Key", width=37, header_style=NULL_STYLE)
        table.add_row(EvToRich("|r---------"), EvToRich("|r----------"),
                      EvToRich("|r-----------------------------"))
        table.add_row(self.generate_compass(looker), col_automap, EvToRich(", ".join(map_legend)))
        yield table

    @group()
    def return_appearance(self, looker, **kwargs):

        if not looker:
            return ""

        def gen_name(obj):
            return obj.get_display_name(looker=looker, pose=True, **kwargs)

        builder = self.locks.check_lockstring(looker, "perm(Builder)")

        yield self.header_line

        yield EvToRich(f"Location: {gen_name(self)}")
        if self.location:
            yield EvToRich(f"Area: {gen_name(self.location)}")

        if builder:
            yield EvToRich(self.generate_builder_info(looker, **kwargs))

        yield self.header_line

        # ourselves
        desc = self.db.desc or "You see nothing special."

        yield EvToRich(desc)

        if settings.AUTOMAP_ENABLED:
            yield self.render_automap(looker, **kwargs)

        yield self.subheader_line

        # contents
        contents_map = self.get_visible_contents(looker, **kwargs)

        if (char_obj := contents_map.get("characters", None)):
            characters = ANSIString("\n").join([gen_name(obj) for obj in char_obj])
            yield EvToRich(characters)

        if (thing_obj := contents_map.get("things", None)):
            things = ANSIString("\n").join([gen_name(obj) for obj in thing_obj])
            yield EvToRich(things)
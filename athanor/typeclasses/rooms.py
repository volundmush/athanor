import typing
from collections import defaultdict
from django.conf import settings

from evennia.utils import evtable, lazy_property
from evennia.utils.ansi import ANSIString
from evennia.objects.objects import DefaultRoom, DefaultObject


import athanor
from .mixin import AthanorObject


class AthanorRoom(AthanorObject, DefaultRoom):
    """
    Not much different from Evennia DefaultRooms.
    """

    lock_default_funcs = athanor.OBJECT_ROOM_DEFAULT_LOCKS
    _content_types = ("room",)
    lockstring = ""

    format_kwargs = ("header", "details", "desc", "subheader", "map", "contents")

    appearance_template = """
{header}
{details}
{header}
{desc}
{map}
{contents}
    """

    def basetype_setup(self):
        """
        Replicates basic basetype_setup,
        but avoids calling super() in order to avoid setting unnecessary locks.
        """
        self.location = None

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

    def at_object_leave(self, moved_obj, target_location, move_type="move", **kwargs):
        super().at_object_leave(
            moved_obj, target_location, move_type=move_type, **kwargs
        )

    def at_object_receive(
        self,
        obj: DefaultObject,
        source_location: typing.Optional[DefaultObject],
        move_type="move",
        **kwargs,
    ):
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

    compass_template = """      ||{N:^3}||
||{NW:>3}|| ||{U:^3}|| ||{NE:<3}||
||{W:>3}|| ||{I:^3}|| ||{E:<3}||
||{SW:>3}|| ||{D:^3}|| ||{SE:<3}||
      ||{S:^3}||
"""

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

        return self.compass_template.format_map(compass_dict).splitlines()

    def generate_map_legend(self, looker, **kwargs) -> list[str]:
        return []

    def generate_builder_info(self, looker, **kwargs):
        return ""

    def get_display_header(self, looker, **kwargs):
        return (
            "O----------------------------------------------------------------------O"
        )

    def get_display_subheader(self, looker, **kwargs):
        return (
            "------------------------------------------------------------------------"
        )

    def get_display_details(self, looker, **kwargs):
        out = []
        builder = self.locks.check_lockstring(looker, "perm(Builder)")

        out.append(f"Location: {self.get_display_name(looker=looker, **kwargs)}")
        if self.location:
            out.append(
                f"Area: {self.location.get_display_name(looker=looker, **kwargs)}"
            )
        if builder:
            out.append(self.generate_builder_info(looker, **kwargs))
        return "\r\n".join(out)

    def get_display_map(self, looker, **kwargs):
        if not settings.AUTOMAP_ENABLED:
            return self.get_display_subheader(looker, **kwargs)
        out = []
        out.append(self.get_display_subheader(looker, **kwargs))
        y_coor = [2, 1, 0, -1, -2]
        x_coor = [-4, -3, -2, -1, 0, 1, 2, 3, 4]
        automap = self.generate_automap(looker, min_x=-4, max_x=4)
        col_automap = ["".join([automap[y][x] for x in x_coor]) for y in y_coor]
        map_legend = self.generate_map_legend(looker, **kwargs)
        compass = self.generate_compass(looker)
        out.append("       Compass        AutoMap                  Map Key|n")
        out.append(
            "|r -----------------   ---------    -------------------------------------|n"
        )
        max_lines = max(len(col_automap), len(map_legend), len(compass))
        for i in range(max_lines):
            compass_line = compass[i] if i < len(compass) else ""
            col_automap_line = col_automap[i] if i < len(col_automap) else ""
            map_legend_line = map_legend[i] if i < len(map_legend) else ""
            sep1 = " " * (20 - len(ANSIString(compass_line)))
            sep2 = " " * (14 - len(ANSIString(col_automap_line)))
            line = " " + compass_line + sep1 + col_automap_line + sep2 + map_legend_line
            out.append(line)
        return "\r\n".join(out)

    def get_list_display_for(self, obj, looker, **kwargs):
        return obj.get_room_display_name(looker=looker, **kwargs)

    def get_display_contents(self, looker, **kwargs):
        contents_map = self.get_visible_contents(looker, **kwargs)
        out = list()

        for content_type in ("characters", "items"):
            if content_obj := contents_map.get(content_type, None):
                for obj in content_obj:
                    out.append(self.get_list_display_for(obj, looker, **kwargs))
        return "\r\n".join(out)

    def get_display_name(self, looker=None, **kwargs):
        return self.attributes.get(key="short_description", default=self.key)

    def get_display_desc(self, looker, **kwargs):
        return self.attributes.get(key="desc", default="").strip("|/")

    def format_appearance(self, appearance, looker, **kwargs):
        return appearance.strip().rstrip("|/")

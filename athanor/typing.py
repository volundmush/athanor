from enum import IntEnum

class ExitDir(IntEnum):
    UNKNOWN = -1
    NORTH = 0
    EAST = 1
    SOUTH = 2
    WEST = 3
    UP = 4
    DOWN = 5
    NORTHWEST = 6
    NORTHEAST = 7
    SOUTHEAST = 8
    SOUTHWEST = 9
    INSIDE = 10
    OUTSIDE = 11

    def reverse(self) -> "ExitDir":
        match self:
            case ExitDir.NORTH:
                return ExitDir.SOUTH
            case ExitDir.EAST:
                return ExitDir.WEST
            case ExitDir.SOUTH:
                return ExitDir.NORTH
            case ExitDir.WEST:
                return ExitDir.EAST
            case ExitDir.UP:
                return ExitDir.DOWN
            case ExitDir.DOWN:
                return ExitDir.UP
            case ExitDir.NORTHWEST:
                return ExitDir.SOUTHEAST
            case ExitDir.NORTHEAST:
                return ExitDir.SOUTHWEST
            case ExitDir.SOUTHEAST:
                return ExitDir.NORTHWEST
            case ExitDir.SOUTHWEST:
                return ExitDir.NORTHEAST
            case ExitDir.INSIDE:
                return ExitDir.OUTSIDE
            case ExitDir.OUTSIDE:
                return ExitDir.INSIDE
            case _:
                return ExitDir.UNKNOWN

    def abbr(self) -> str:
        match self:
            case ExitDir.NORTH:
                return "N"
            case ExitDir.EAST:
                return "W"
            case ExitDir.SOUTH:
                return "S"
            case ExitDir.WEST:
                return "W"
            case ExitDir.UP:
                return "U"
            case ExitDir.DOWN:
                return "D"
            case ExitDir.NORTHWEST:
                return "NW"
            case ExitDir.NORTHEAST:
                return "NE"
            case ExitDir.SOUTHEAST:
                return "SE"
            case ExitDir.SOUTHWEST:
                return "SW"
            case ExitDir.INSIDE:
                return "I"
            case ExitDir.OUTSIDE:
                return "O"
            case _:
                return "--"


NAME_TO_ENUM = {
    "north": ExitDir.NORTH,
    "east": ExitDir.EAST,
    "south": ExitDir.SOUTH,
    "west": ExitDir.WEST,
    "up": ExitDir.UP,
    "down": ExitDir.DOWN,
    "northwest": ExitDir.NORTHWEST,
    "northeast": ExitDir.NORTHEAST,
    "southeast": ExitDir.SOUTHEAST,
    "southwest": ExitDir.SOUTHWEST,
    "inside": ExitDir.INSIDE,
    "outside": ExitDir.OUTSIDE,
}
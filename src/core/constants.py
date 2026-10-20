from enum import Enum, IntEnum, auto


Pos = tuple[int, int]


class Direction(IntEnum):
    UP = 0
    DOWN = 1
    LEFT = 2
    RIGHT = 3


class Orientation(IntEnum):
    STANDING = 0
    HORIZONTAL = 1
    VERTICAL = 2


class Tile:
    VOID = "."
    FLOOR = "#"
    START = "S"
    GOAL = "G"
    FRAGILE = "F"


class Outcome(Enum):
    OK = auto()
    FELL = auto()
    FRAGILE_BROKE = auto()
    BLOCKED = auto()
    INVALID_ACTION = auto()
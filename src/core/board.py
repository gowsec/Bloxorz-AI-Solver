"""Core board data, including handwritten levels, bridges and switches."""

from dataclasses import dataclass
from enum import Enum
from typing import Iterable

from src.core.constants import Pos


class SwitchType(Enum):
    SOFT = "soft"
    HEAVY = "heavy"
    SPLIT = "split"


class EffectMode(Enum):
    TOGGLE = "toggle"
    SET_OPEN = "set_open"
    SET_CLOSE = "set_close"


@dataclass(frozen=True, slots=True)
class Bridge:
    pos: Pos
    initial_open: bool


@dataclass(frozen=True, slots=True)
class Effect:
    mode: EffectMode
    bridges: tuple[int, ...]
    mask: int

    @staticmethod
    def create(mode: EffectMode, bridge_ids: Iterable[int]) -> "Effect":
        ids = tuple(sorted(set(bridge_ids)))
        if not ids:
            raise ValueError("An effect must target at least one bridge")

        mask = 0
        for bridge_id in ids:
            if bridge_id < 0:
                raise ValueError("Bridge IDs must be non-negative")
            mask |= 1 << bridge_id

        return Effect(mode, ids, mask)


@dataclass(frozen=True, slots=True)
class Switch:
    pos: Pos
    type: SwitchType
    effect: Effect | None = None
    split_targets: tuple[Pos, Pos] | None = None


@dataclass(frozen=True)
class Level:
    name: str
    rows: int
    cols: int
    terrain: tuple[str, ...]
    start: Pos
    goal: Pos
    bridges: dict[int, Bridge]
    bridge_at: dict[Pos, int]
    switches: dict[Pos, Switch]

    @classmethod
    def from_grid(cls, name: str, grid: tuple[str, ...]) -> "Level":
        """Create a basic handwritten level without bridges or switches.

        Coordinates use (row, column), starting at zero.
        Allowed tiles: . (void), # (floor), S (start), G (goal), F (fragile).
        """
        grid = tuple(grid)

        if not grid or not grid[0] or any(
            len(row) != len(grid[0]) for row in grid
        ):
            raise ValueError("Level grid must be non-empty and rectangular")

        if any(cell not in ".#SGF" for row in grid for cell in row):
            raise ValueError("Allowed tiles: . # S G F")

        starts = [
            (r, c)
            for r, row in enumerate(grid)
            for c, cell in enumerate(row)
            if cell == "S"
        ]
        goals = [
            (r, c)
            for r, row in enumerate(grid)
            for c, cell in enumerate(row)
            if cell == "G"
        ]

        if len(starts) != 1 or len(goals) != 1:
            raise ValueError("Level needs exactly one S and one G")

        terrain = tuple(
            row.replace("S", "#").replace("G", "#")
            for row in grid
        )

        return cls(
            name=name,
            rows=len(grid),
            cols=len(grid[0]),
            terrain=terrain,
            start=starts[0],
            goal=goals[0],
            bridges={},
            bridge_at={},
            switches={},
        )
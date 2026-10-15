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
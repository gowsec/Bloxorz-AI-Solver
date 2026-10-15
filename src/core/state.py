from dataclasses import dataclass

from src.core.constants import Orientation, Pos


@dataclass(frozen=True, slots=True)
class BlockPose:
    r: int
    c: int
    orient: Orientation


@dataclass(frozen=True, slots=True)
class SplitPose:
    a: Pos
    b: Pos


@dataclass(frozen=True, slots=True)
class State:
    pose: BlockPose | SplitPose
    bridges: int


def cells(pose: BlockPose | SplitPose) -> tuple[Pos, ...]:
    if isinstance(pose, SplitPose):
        return (pose.a, pose.b)
    if pose.orient is Orientation.STANDING:
        return ((pose.r, pose.c),)
    if pose.orient is Orientation.HORIZONTAL:
        return ((pose.r, pose.c), (pose.r, pose.c + 1))
    return ((pose.r, pose.c), (pose.r + 1, pose.c))


def is_split(state: State) -> bool:
    return isinstance(state.pose, SplitPose)
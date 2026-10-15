from dataclasses import dataclass

from src.core.constants import Direction, Orientation
from src.core.state import BlockPose


@dataclass(frozen=True, slots=True)
class Action:
    direction: Direction
    cube: int | None = None


def move_block(pose: BlockPose, direction: Direction) -> BlockPose:
    r, c, orientation = pose.r, pose.c, pose.orient
    transitions = {
        (Orientation.STANDING, Direction.UP): BlockPose(r - 2, c, Orientation.VERTICAL),
        (Orientation.STANDING, Direction.DOWN): BlockPose(r + 1, c, Orientation.VERTICAL),
        (Orientation.STANDING, Direction.LEFT): BlockPose(r, c - 2, Orientation.HORIZONTAL),
        (Orientation.STANDING, Direction.RIGHT): BlockPose(r, c + 1, Orientation.HORIZONTAL),
        (Orientation.HORIZONTAL, Direction.UP): BlockPose(r - 1, c, Orientation.HORIZONTAL),
        (Orientation.HORIZONTAL, Direction.DOWN): BlockPose(r + 1, c, Orientation.HORIZONTAL),
        (Orientation.HORIZONTAL, Direction.LEFT): BlockPose(r, c - 1, Orientation.STANDING),
        (Orientation.HORIZONTAL, Direction.RIGHT): BlockPose(r, c + 2, Orientation.STANDING),
        (Orientation.VERTICAL, Direction.UP): BlockPose(r - 1, c, Orientation.STANDING),
        (Orientation.VERTICAL, Direction.DOWN): BlockPose(r + 2, c, Orientation.STANDING),
        (Orientation.VERTICAL, Direction.LEFT): BlockPose(r, c - 1, Orientation.VERTICAL),
        (Orientation.VERTICAL, Direction.RIGHT): BlockPose(r, c + 1, Orientation.VERTICAL),
    }
    return transitions[(orientation, direction)]
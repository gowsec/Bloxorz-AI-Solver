from dataclasses import dataclass

from src.core.constants import Direction, Orientation
from src.core.state import BlockPose


@dataclass(frozen=True, slots=True)
class Action:
    direction: Direction
    cube: int | None = None


_TRANSITIONS = {
    (Orientation.STANDING, Direction.UP): (-2, 0, Orientation.VERTICAL),
    (Orientation.STANDING, Direction.DOWN): (1, 0, Orientation.VERTICAL),
    (Orientation.STANDING, Direction.LEFT): (0, -2, Orientation.HORIZONTAL),
    (Orientation.STANDING, Direction.RIGHT): (0, 1, Orientation.HORIZONTAL),
    (Orientation.HORIZONTAL, Direction.UP): (-1, 0, Orientation.HORIZONTAL),
    (Orientation.HORIZONTAL, Direction.DOWN): (1, 0, Orientation.HORIZONTAL),
    (Orientation.HORIZONTAL, Direction.LEFT): (0, -1, Orientation.STANDING),
    (Orientation.HORIZONTAL, Direction.RIGHT): (0, 2, Orientation.STANDING),
    (Orientation.VERTICAL, Direction.UP): (-1, 0, Orientation.STANDING),
    (Orientation.VERTICAL, Direction.DOWN): (2, 0, Orientation.STANDING),
    (Orientation.VERTICAL, Direction.LEFT): (0, -1, Orientation.VERTICAL),
    (Orientation.VERTICAL, Direction.RIGHT): (0, 1, Orientation.VERTICAL),
}


def move_block(pose: BlockPose, direction: Direction) -> BlockPose:
    dr, dc, orientation = _TRANSITIONS[(pose.orient, direction)]
    return BlockPose(pose.r + dr, pose.c + dc, orientation)

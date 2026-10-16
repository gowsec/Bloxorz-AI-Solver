from src.core.constants import Direction, Orientation
from src.core.move import BlockPose, move_block


def test_standing_moves():
    p = BlockPose(3, 3, Orientation.STANDING)
    assert move_block(p, Direction.UP) == BlockPose(1, 3, Orientation.VERTICAL)
    assert move_block(p, Direction.DOWN) == BlockPose(4, 3, Orientation.VERTICAL)
    assert move_block(p, Direction.LEFT) == BlockPose(3, 1, Orientation.HORIZONTAL)
    assert move_block(p, Direction.RIGHT) == BlockPose(3, 4, Orientation.HORIZONTAL)


def test_horizontal_moves():
    p = BlockPose(3, 3, Orientation.HORIZONTAL)  # occupies (3,3) and (3,4)
    assert move_block(p, Direction.UP) == BlockPose(2, 3, Orientation.HORIZONTAL)
    assert move_block(p, Direction.DOWN) == BlockPose(4, 3, Orientation.HORIZONTAL)
    assert move_block(p, Direction.LEFT) == BlockPose(3, 2, Orientation.STANDING)
    assert move_block(p, Direction.RIGHT) == BlockPose(3, 5, Orientation.STANDING)


def test_vertical_moves():
    p = BlockPose(3, 3, Orientation.VERTICAL)  # occupies (3,3) and (4,3)
    assert move_block(p, Direction.UP) == BlockPose(2, 3, Orientation.STANDING)
    assert move_block(p, Direction.DOWN) == BlockPose(5, 3, Orientation.STANDING)
    assert move_block(p, Direction.LEFT) == BlockPose(3, 2, Orientation.VERTICAL)
    assert move_block(p, Direction.RIGHT) == BlockPose(3, 4, Orientation.VERTICAL)

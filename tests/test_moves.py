from src.core.constants import Direction, Orientation
from src.core.move import BlockPose, move_block
from src.core.state import cells


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


def test_cells():
    assert cells(BlockPose(3, 3, Orientation.STANDING)) == ((3, 3),)
    assert cells(BlockPose(3, 3, Orientation.HORIZONTAL)) == ((3, 3), (3, 4))
    assert cells(BlockPose(3, 3, Orientation.VERTICAL)) == ((3, 3), (4, 3))


def test_move_reversibility():
    p = BlockPose(3, 3, Orientation.STANDING)
    
    # Standing -> Vertical -> Standing
    p_up = move_block(p, Direction.UP)
    assert move_block(p_up, Direction.DOWN) == p
    
    p_down = move_block(p, Direction.DOWN)
    assert move_block(p_down, Direction.UP) == p
    
    # Standing -> Horizontal -> Standing
    p_left = move_block(p, Direction.LEFT)
    assert move_block(p_left, Direction.RIGHT) == p
    
    p_right = move_block(p, Direction.RIGHT)
    assert move_block(p_right, Direction.LEFT) == p

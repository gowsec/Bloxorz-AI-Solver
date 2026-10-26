"""Test riêng cho mechanics/split.py (tách và ghép khối)."""
import pytest

from src.core.constants import Orientation
from src.core.state import BlockPose, SplitPose, State
from src.mechanics.split import merge_if_adjacent, split_block

STANDING = BlockPose(0, 0, Orientation.STANDING)


def test_split_block_keeps_target_order():
    """Khối lập phương số 0 là targets[0], số 1 là targets[1]."""
    assert split_block(STANDING, ((1, 0), (1, 3))) == SplitPose((1, 0), (1, 3))
    assert split_block(STANDING, ((1, 3), (1, 0))) == SplitPose((1, 3), (1, 0))


@pytest.mark.parametrize("orient", [Orientation.HORIZONTAL, Orientation.VERTICAL])
def test_only_a_standing_block_can_split(orient):
    with pytest.raises(ValueError):
        split_block(BlockPose(0, 0, orient), ((1, 0), (1, 3)))


def test_split_result_is_hashable_even_if_targets_are_lists():
    """State phải hashable để vào set/dict; nếu loader để split_targets là list thì vẫn không được lỗi."""
    state = State(split_block(STANDING, ([1, 0], [1, 3])), 0)
    assert hash(state) == hash(State(SplitPose((1, 0), (1, 3)), 0))


@pytest.mark.parametrize(
    "a, b, expected",
    [
        ((2, 3), (2, 4), BlockPose(2, 3, Orientation.HORIZONTAL)),
        ((2, 4), (2, 3), BlockPose(2, 3, Orientation.HORIZONTAL)),   # a ở bên phải b
        ((2, 3), (3, 3), BlockPose(2, 3, Orientation.VERTICAL)),
        ((3, 3), (2, 3), BlockPose(2, 3, Orientation.VERTICAL)),     # a ở bên dưới b
    ],
)
def test_merge_adjacent_cubes_anchors_at_top_left(a, b, expected):
    assert merge_if_adjacent(SplitPose(a, b)) == expected


@pytest.mark.parametrize(
    "a, b",
    [((2, 3), (3, 4)), ((2, 3), (2, 5)), ((2, 3), (4, 3)), ((2, 3), (2, 3))],
    ids=["cheo", "cach-2-ngang", "cach-2-doc", "trung-o"],
)
def test_merge_ignores_non_adjacent_cubes(a, b):
    pose = SplitPose(a, b)
    assert merge_if_adjacent(pose) is pose

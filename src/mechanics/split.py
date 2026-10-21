from src.core.constants import Orientation
from src.core.state import BlockPose, SplitPose


def merge_if_adjacent(pose: SplitPose) -> BlockPose | SplitPose:
    (ar, ac), (br, bc) = pose.a, pose.b
    if ar == br and abs(ac - bc) == 1:
        return BlockPose(ar, min(ac, bc), Orientation.HORIZONTAL)
    if ac == bc and abs(ar - br) == 1:
        return BlockPose(min(ar, br), ac, Orientation.VERTICAL)
    return pose
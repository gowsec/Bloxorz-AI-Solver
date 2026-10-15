from src.core.board import Level
from src.core.constants import Orientation, Outcome
from src.core.state import BlockPose, SplitPose, cells


def support_failure(level: Level, pose: BlockPose | SplitPose, bridges: int) -> Outcome | None:
    for r, c in cells(pose):
        if not (0 <= r < level.rows and 0 <= c < level.cols):
            return Outcome.FELL

        pos = (r, c)
        bridge_id = level.bridge_at.get(pos)
        if bridge_id is not None:
            if not bridges & (1 << bridge_id):
                return Outcome.FELL
            continue

        tile = level.terrain[r][c]
        if tile == ".":
            return Outcome.FELL
        if (
            tile == "F"
            and isinstance(pose, BlockPose)
            and pose.orient is Orientation.STANDING
        ):
            return Outcome.FRAGILE_BROKE
    return None
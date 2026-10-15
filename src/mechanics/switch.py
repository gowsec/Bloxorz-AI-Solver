from src.core.board import Level, Switch, SwitchType
from src.core.constants import Orientation, Pos
from src.core.state import BlockPose, SplitPose
from src.mechanics.bridge import apply_effect


def activated_switches(
    level: Level,
    landed_cells: tuple[Pos, ...],
    pose: BlockPose | SplitPose,
) -> tuple[Switch, ...]:
    activated = []
    for pos in sorted(set(landed_cells)):
        switch = level.switches.get(pos)
        if switch is None:
            continue
        if switch.type is SwitchType.SOFT:
            activated.append(switch)
        elif (
            switch.type is SwitchType.HEAVY
            and isinstance(pose, BlockPose)
            and pose.orient is Orientation.STANDING
        ):
            activated.append(switch)
        elif (
            switch.type is SwitchType.SPLIT
            and isinstance(pose, BlockPose)
            and pose.orient is Orientation.STANDING
        ):
            activated.append(switch)
    return tuple(activated)


def apply_switch_effects(bridges: int, switches: tuple[Switch, ...]) -> int:
    for switch in switches:
        if switch.type in (SwitchType.SOFT, SwitchType.HEAVY):
            if switch.effect is not None:
                bridges = apply_effect(bridges, switch.effect)
    return bridges
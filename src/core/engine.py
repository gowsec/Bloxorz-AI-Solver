from src.core.board import Level, SwitchType
from src.core.constants import Direction, Orientation, Outcome, Pos
from src.core.move import Action, move_block
from src.core.state import BlockPose, SplitPose, State, cells
from src.mechanics.bridge import initial_bridges
from src.mechanics.fragile import support_failure
from src.mechanics.split import merge_if_adjacent, split_block
from src.mechanics.switch import activated_switches, apply_switch_effects


class Engine:
    def __init__(self, level: Level):
        self.level = level

    def initial_state(self) -> State:
        return State(BlockPose(*self.level.start, Orientation.STANDING), initial_bridges(self.level))

    def get_actions(self, state: State) -> list[Action]:
        if self.is_goal(state):
            return []
        if isinstance(state.pose, BlockPose):
            return [Action(direction) for direction in Direction]
        return [Action(direction, cube) for direction in Direction for cube in (0, 1)]

    def try_step(self, state: State, action: Action) -> tuple[State | None, Outcome]:
        if self.is_goal(state):
            return None, Outcome.INVALID_ACTION

        pose = state.pose
        if not isinstance(action, Action) or not isinstance(action.direction, Direction):
            return None, Outcome.INVALID_ACTION
        if isinstance(pose, BlockPose):
            if action.cube is not None:
                return None, Outcome.INVALID_ACTION
            moved_pose = move_block(pose, action.direction)
            landed = cells(moved_pose)
            was_split = False
        else:
            if action.cube not in (0, 1):
                return None, Outcome.INVALID_ACTION
            old_cells = [pose.a, pose.b]
            destination = self._move_cell(old_cells[action.cube], action.direction)
            if destination == old_cells[1 - action.cube]:
                return None, Outcome.BLOCKED
            old_cells[action.cube] = destination
            moved_pose = SplitPose(old_cells[0], old_cells[1])
            landed = (destination,)
            was_split = True

        failure = support_failure(self.level, moved_pose, state.bridges)
        if failure is not None:
            return None, failure

        activated = activated_switches(self.level, landed, moved_pose)
        new_bridges = apply_switch_effects(state.bridges, activated)
        failure = support_failure(self.level, moved_pose, new_bridges)
        if failure is not None:
            return None, Outcome.FELL

        split_switch = next(
            (switch for switch in activated if switch.type is SwitchType.SPLIT),
            None,
        )
        if split_switch is not None:
            if split_switch.split_targets is None:
                raise ValueError("Split switch must define split_targets")
            if not isinstance(moved_pose, BlockPose):
                raise ValueError("Only an intact block can activate a split switch")
            moved_pose = split_block(moved_pose, split_switch.split_targets)
        elif was_split:
            moved_pose = merge_if_adjacent(moved_pose)

        return State(moved_pose, new_bridges), Outcome.OK

    def step(self, state: State, action: Action) -> State | None:
        next_state, outcome = self.try_step(state, action)
        return next_state if outcome is Outcome.OK else None

    def get_successors(self, state: State) -> list[tuple[Action, State]]:
        successors = []
        for action in self.get_actions(state):
            next_state = self.step(state, action)
            if next_state is not None:
                successors.append((action, next_state))
        return successors

    def is_goal(self, state: State) -> bool:
        pose = state.pose
        return (
            isinstance(pose, BlockPose)
            and pose.orient is Orientation.STANDING
            and (pose.r, pose.c) == self.level.goal
        )

    @staticmethod
    def _move_cell(pos: Pos, direction: Direction) -> Pos:
        dr, dc = {
            Direction.UP: (-1, 0),
            Direction.DOWN: (1, 0),
            Direction.LEFT: (0, -1),
            Direction.RIGHT: (0, 1),
        }[direction]
        return pos[0] + dr, pos[1] + dc
import pytest

from src.core.board import Bridge, Effect, EffectMode, Level, Switch, SwitchType
from src.core.constants import Direction, Orientation, Outcome
from src.core.engine import Engine
from src.core.move import Action
from src.core.state import BlockPose, SplitPose, State
from src.mechanics.bridge import apply_effect, initial_bridges


def make_level(
    terrain: tuple[str, ...],
    bridges: dict[int, Bridge] | None = None,
    switches: dict[tuple[int, int], Switch] | None = None,
) -> Level:
    bridges = bridges or {}
    return Level(
        name="test",
        rows=len(terrain),
        cols=len(terrain[0]),
        terrain=terrain,
        start=(0, 0),
        goal=(0, len(terrain[0]) - 1),
        bridges=bridges,
        bridge_at={bridge.pos: bridge_id for bridge_id, bridge in bridges.items()},
        switches=switches or {},
    )


def test_initial_bridges_uses_bridge_ids_as_bit_positions():
    level = make_level(("S..G",), {0: Bridge((0, 1), True), 1: Bridge((0, 2), False)})

    assert initial_bridges(level) == 0b01


@pytest.mark.parametrize(
    ("mode", "expected"),
    [
        (EffectMode.TOGGLE, 0b101 ^ 0b110),
        (EffectMode.SET_OPEN, 0b111),
        (EffectMode.SET_CLOSE, 0b001),
    ],
)
def test_apply_effect_changes_only_targeted_bits(mode, expected):
    effect = Effect.create(mode, (1, 2))

    assert apply_effect(0b101, effect) == expected


def test_toggle_twice_restores_original_mask():
    effect = Effect.create(EffectMode.TOGGLE, (0, 3))
    initial = 0b0110

    assert apply_effect(apply_effect(initial, effect), effect) == initial


@pytest.mark.parametrize("mode", [EffectMode.SET_OPEN, EffectMode.SET_CLOSE])
def test_set_effect_is_idempotent(mode):
    effect = Effect.create(mode, (1, 2))
    once = apply_effect(0b1001, effect)

    assert apply_effect(once, effect) == once


def test_effect_factory_sorts_and_deduplicates_bridge_ids():
    effect = Effect.create(EffectMode.TOGGLE, (3, 1, 3))

    assert effect.bridges == (1, 3)
    assert effect.mask == 0b1010


@pytest.mark.parametrize("bridge_ids", [(), (-1,)])
def test_effect_factory_rejects_empty_or_negative_bridge_ids(bridge_ids):
    with pytest.raises(ValueError):
        Effect.create(EffectMode.TOGGLE, bridge_ids)


def test_apply_effect_rejects_unknown_mode():
    effect = Effect(mode="unknown", bridges=(0,), mask=0b1)

    with pytest.raises(ValueError, match="Unsupported effect mode"):
        apply_effect(0b1, effect)


def test_soft_switch_opens_bridge_and_updates_state():
    effect = Effect.create(EffectMode.SET_OPEN, (0,))
    level = make_level(
        ("S##.G",),
        {0: Bridge((0, 3), False)},
        {(0, 1): Switch((0, 1), SwitchType.SOFT, effect=effect)},
    )

    state, outcome = Engine(level).try_step(
        Engine(level).initial_state(), Action(Direction.RIGHT)
    )

    assert outcome is Outcome.OK
    assert state.bridges == 1
    assert state.pose == BlockPose(0, 1, Orientation.HORIZONTAL)


def test_switch_closing_bridge_under_block_causes_fall():
    effect = Effect.create(EffectMode.SET_CLOSE, (0,))
    level = make_level(
        ("S#..G",),
        {0: Bridge((0, 2), True)},
        {(0, 1): Switch((0, 1), SwitchType.SOFT, effect=effect)},
    )

    state, outcome = Engine(level).try_step(
        Engine(level).initial_state(), Action(Direction.RIGHT)
    )

    assert state is None
    assert outcome is Outcome.FELL


def test_heavy_switch_only_activates_when_block_stands_on_it():
    effect = Effect.create(EffectMode.SET_OPEN, (0,))
    level = make_level(
        ("S###.G",),
        {0: Bridge((0, 4), False)},
        {(0, 3): Switch((0, 3), SwitchType.HEAVY, effect=effect)},
    )
    engine = Engine(level)
    horizontal_state = State(BlockPose(0, 1, Orientation.HORIZONTAL), 0)

    state, outcome = engine.try_step(horizontal_state, Action(Direction.RIGHT))

    assert outcome is Outcome.OK
    assert state.bridges == 1
    assert state.pose == BlockPose(0, 3, Orientation.STANDING)


def test_heavy_switch_does_not_activate_when_block_is_horizontal():
    effect = Effect.create(EffectMode.SET_OPEN, (0,))
    level = make_level(
        ("S###G",),
        {0: Bridge((0, 3), False)},
        {(0, 1): Switch((0, 1), SwitchType.HEAVY, effect=effect)},
    )

    state, outcome = Engine(level).try_step(
        Engine(level).initial_state(), Action(Direction.RIGHT)
    )

    assert outcome is Outcome.OK
    assert state.bridges == 0
    assert state.pose == BlockPose(0, 1, Orientation.HORIZONTAL)


def test_soft_switch_activates_when_split_cube_moves_onto_it():
    effect = Effect.create(EffectMode.TOGGLE, (0,))
    level = make_level(
        ("S##G",),
        {0: Bridge((0, 3), False)},
        {(0, 1): Switch((0, 1), SwitchType.SOFT, effect=effect)},
    )
    state = State(SplitPose((0, 0), (0, 2)), 0)

    next_state, outcome = Engine(level).try_step(
        state, Action(Direction.RIGHT, cube=0)
    )

    assert outcome is Outcome.OK
    assert next_state.bridges == 1
    assert next_state.pose == BlockPose(0, 1, Orientation.HORIZONTAL)


def test_standing_on_fragile_tile_fails():
    level = make_level(("S##F",))
    state = State(BlockPose(0, 1, Orientation.HORIZONTAL), 0)

    next_state, outcome = Engine(level).try_step(state, Action(Direction.RIGHT))

    assert next_state is None
    assert outcome is Outcome.FRAGILE_BROKE


def test_nonstanding_block_can_span_fragile_tile():
    level = make_level(("S#F#G",))
    state = State(BlockPose(0, 0, Orientation.STANDING), 0)

    next_state, outcome = Engine(level).try_step(state, Action(Direction.RIGHT))

    assert outcome is Outcome.OK
    assert next_state.pose == BlockPose(0, 1, Orientation.HORIZONTAL)


def test_split_switch_splits_standing_block():
    split = Switch(
        (0, 2),
        SwitchType.SPLIT,
        split_targets=((1, 0), (1, 3)),
    )
    level = make_level(("S###G", "#####"), switches={(0, 2): split})
    state = State(BlockPose(0, 0, Orientation.HORIZONTAL), 0)

    next_state, outcome = Engine(level).try_step(state, Action(Direction.RIGHT))

    assert outcome is Outcome.OK
    assert next_state.pose == SplitPose((1, 0), (1, 3))


def test_split_switch_does_not_split_horizontal_block():
    split = Switch(
        (0, 1),
        SwitchType.SPLIT,
        split_targets=((1, 0), (1, 3)),
    )
    level = make_level(("S##G", "####"), switches={(0, 1): split})

    next_state, outcome = Engine(level).try_step(
        Engine(level).initial_state(), Action(Direction.RIGHT)
    )

    assert outcome is Outcome.OK
    assert next_state.pose == BlockPose(0, 1, Orientation.HORIZONTAL)


def test_adjacent_split_cubes_merge_after_move_without_retriggering_switch():
    effect = Effect.create(EffectMode.TOGGLE, (0,))
    level = make_level(
        ("S##G",),
        {0: Bridge((0, 3), False)},
        {(0, 1): Switch((0, 1), SwitchType.SOFT, effect=effect)},
    )
    state = State(SplitPose((0, 0), (0, 2)), 0)

    next_state, outcome = Engine(level).try_step(state, Action(Direction.LEFT, cube=1))

    assert outcome is Outcome.OK
    assert next_state.pose == BlockPose(0, 0, Orientation.HORIZONTAL)
    assert next_state.bridges == 1


def test_split_cubes_cannot_move_onto_each_other():
    level = make_level(("S##G",))
    state = State(SplitPose((0, 0), (0, 1)), 0)

    next_state, outcome = Engine(level).try_step(state, Action(Direction.RIGHT, cube=0))

    assert next_state is None
    assert outcome is Outcome.BLOCKED


def test_invalid_action_for_blocked_state_is_reported():
    level = make_level(("S#G",))

    next_state, outcome = Engine(level).try_step(
        Engine(level).initial_state(), Action(Direction.RIGHT, cube=0)
    )

    assert next_state is None
    assert outcome is Outcome.INVALID_ACTION

def test_closed_bridge_blocks_and_open_bridge_supports():
    for open_, expected in ((False, Outcome.FELL), (True, Outcome.OK)):
        level = make_level(("S#.G",), {0: Bridge((0, 2), open_)})
        _, outcome = Engine(level).try_step(Engine(level).initial_state(), Action(Direction.RIGHT))
        assert outcome is expected
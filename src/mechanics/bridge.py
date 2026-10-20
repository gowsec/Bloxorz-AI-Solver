from src.core.board import Effect, EffectMode, Level


def initial_bridges(level: Level) -> int:
    mask = 0
    for bridge_id, bridge in level.bridges.items():
        if bridge.initial_open:
            mask |= 1 << bridge_id
    return mask


def apply_effect(bridges: int, effect: Effect) -> int:
    if effect.mode is EffectMode.TOGGLE:
        return bridges ^ effect.mask
    if effect.mode is EffectMode.SET_OPEN:
        return bridges | effect.mask
    if effect.mode is EffectMode.SET_CLOSE:
        return bridges & ~effect.mask
    raise ValueError(f"Unsupported effect mode: {effect.mode!r}")
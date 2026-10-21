import json
from pathlib import Path
from typing import Any

from src.core.board import Bridge, Effect, EffectMode, Level, Switch, SwitchType
from src.core.constants import Pos, Tile


def load_level(file_path: str | Path) -> Level:
    path = Path(file_path)
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    name = data.get("name", "Unknown Level")
    grid_raw = data.get("grid", [])

    # 2. Check grid properties
    if not grid_raw:
        raise ValueError(f"[{path}] Grid is empty or missing")
    rows = len(grid_raw)
    cols = len(grid_raw[0])
    if cols == 0:
        raise ValueError(f"[{path}] Grid rows must not be empty")

    terrain = []
    starts = []
    goals = []

    for r, row in enumerate(grid_raw):
        if len(row) != cols:
            raise ValueError(f"[{path}] Row {r} has inconsistent length")
        terrain_row = ""
        for c, char in enumerate(row):
            if char not in (Tile.VOID, Tile.FLOOR, Tile.START, Tile.GOAL, Tile.FRAGILE):
                raise ValueError(f"[{path}] Invalid character '{char}' at ({r}, {c})")
            
            if char == Tile.START:
                starts.append((r, c))
                terrain_row += Tile.FLOOR  # START is a floor tile
            elif char == Tile.GOAL:
                goals.append((r, c))
                terrain_row += Tile.GOAL
            else:
                terrain_row += char
        terrain.append(terrain_row)

    # 1. Check exactly one S and one G
    if len(starts) != 1:
        raise ValueError(f"[{path}] Level must have exactly one start point 'S', found {len(starts)}")
    if len(goals) != 1:
        raise ValueError(f"[{path}] Level must have exactly one goal point 'G', found {len(goals)}")

    start_pos = starts[0]
    goal_pos = goals[0]

    # 3. Bridges
    bridges = {}
    bridge_at = {}
    bridges_data = data.get("bridges", [])
    expected_ids = set(range(len(bridges_data)))
    actual_ids = set()

    for b_data in bridges_data:
        b_id = b_data.get("id")
        if b_id is None:
             raise ValueError(f"[{path}] Bridge is missing 'id'")
        if b_id in actual_ids:
            raise ValueError(f"[{path}] Duplicate bridge id: {b_id}")
        
        pos = tuple(b_data.get("pos"))
        if len(pos) != 2:
            raise ValueError(f"[{path}] Invalid bridge position: {pos}")
        r, c = pos
        if not (0 <= r < rows and 0 <= c < cols):
            raise ValueError(f"[{path}] Bridge {b_id} position {pos} out of bounds")
        if terrain[r][c] != Tile.VOID:
            raise ValueError(f"[{path}] Bridge {b_id} at {pos} must be on a VOID tile")
        if pos in bridge_at:
             raise ValueError(f"[{path}] Multiple bridges at {pos}")

        bridges[b_id] = Bridge(pos=(r, c), initial_open=b_data.get("initial_open", False))
        bridge_at[(r, c)] = b_id
        actual_ids.add(b_id)

    if actual_ids != expected_ids:
        raise ValueError(f"[{path}] Bridge IDs must be continuous from 0 to {len(bridges_data)-1}")

    if len(bridges) > 62:
        raise ValueError(f"[{path}] Number of bridges exceeds maximum limit of 62")

    # 4. Switches
    switches = {}
    switches_data = data.get("switches", [])
    for s_data in switches_data:
        pos_raw = s_data.get("pos")
        if not pos_raw or len(pos_raw) != 2:
            raise ValueError(f"[{path}] Invalid switch position: {pos_raw}")
        pos = (pos_raw[0], pos_raw[1])
        r, c = pos
        
        if not (0 <= r < rows and 0 <= c < cols):
            raise ValueError(f"[{path}] Switch at {pos} out of bounds")
        if terrain[r][c] != Tile.FLOOR:
             raise ValueError(f"[{path}] Switch at {pos} must be on a FLOOR tile")
        if pos == start_pos:
             raise ValueError(f"[{path}] Switch at {pos} cannot be on the Start tile (S)")
        if pos in switches:
            raise ValueError(f"[{path}] Multiple switches at {pos}")
        if pos in bridge_at:
             raise ValueError(f"[{path}] Switch at {pos} cannot be on a bridge")

        s_type_raw = s_data.get("type")
        try:
            s_type = SwitchType(s_type_raw)
        except ValueError:
            raise ValueError(f"[{path}] Invalid switch type: {s_type_raw}")

        effect = None
        split_targets = None

        if s_type in (SwitchType.SOFT, SwitchType.HEAVY):
            eff_data = s_data.get("effect")
            if not eff_data:
                 raise ValueError(f"[{path}] {s_type.value} switch at {pos} missing 'effect'")
            
            mode_raw = eff_data.get("mode")
            try:
                mode = EffectMode(mode_raw)
            except ValueError:
                raise ValueError(f"[{path}] Invalid effect mode: {mode_raw}")
            
            b_ids = eff_data.get("bridges", [])
            if not b_ids:
                 raise ValueError(f"[{path}] Effect at {pos} must target at least one bridge")
            for b_id in b_ids:
                if b_id not in bridges:
                    raise ValueError(f"[{path}] Effect at {pos} refers to non-existent bridge id {b_id}")
            
            effect = Effect.create(mode, b_ids)
        
        elif s_type == SwitchType.SPLIT:
            targets_raw = s_data.get("split_targets")
            if not targets_raw or len(targets_raw) != 2:
                 raise ValueError(f"[{path}] Split switch at {pos} missing or invalid 'split_targets'")
            
            targets = []
            for t_raw in targets_raw:
                if len(t_raw) != 2:
                     raise ValueError(f"[{path}] Invalid split target: {t_raw}")
                tr, tc = t_raw
                if not (0 <= tr < rows and 0 <= tc < cols):
                    raise ValueError(f"[{path}] Split target {t_raw} out of bounds")
                # Rule 6: sàn hợp lệ (không phải VOID, cầu, dễ vỡ)
                if terrain[tr][tc] != Tile.FLOOR:
                     raise ValueError(f"[{path}] Split target {t_raw} must be a regular FLOOR tile")
                targets.append((tr, tc))
            
            # Rule 6: không kề cạnh
            t0, t1 = targets[0], targets[1]
            if abs(t0[0] - t1[0]) + abs(t0[1] - t1[1]) <= 1:
                 raise ValueError(f"[{path}] Split targets {t0} and {t1} must not be adjacent")
            
            split_targets = (targets[0], targets[1])

        switches[pos] = Switch(pos=pos, type=s_type, effect=effect, split_targets=split_targets)

    switch_positions = set(switches.keys())
    for switch in switches.values():
        if switch.type == SwitchType.SPLIT:
            t0, t1 = switch.split_targets
            if t0 in switch_positions or t1 in switch_positions:
                raise ValueError(f"[{path}] Split targets {t0} and {t1} must not overlap with any switch")

    return Level(
        name=name,
        rows=rows,
        cols=cols,
        terrain=tuple(terrain),
        start=start_pos,
        goal=goal_pos,
        bridges=bridges,
        bridge_at=bridge_at,
        switches=switches,
    )

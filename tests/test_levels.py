import json
import pytest
from src.utils.json_loader import load_level
from src.core.board import SwitchType, EffectMode

def test_load_valid_level(tmp_path):
    level_data = {
        "name": "Test Level",
        "grid": [
            "S#..",
            "##..",
            "...G"
        ],
        "bridges": [
            {"id": 0, "pos": [2, 2], "initial_open": False}
        ],
        "switches": [
            {
                "pos": [0, 1],
                "type": "soft",
                "effect": { "mode": "toggle", "bridges": [0] }
            }
        ]
    }
    level_file = tmp_path / "test_level.json"
    with open(level_file, "w") as f:
        json.dump(level_data, f)
    
    level = load_level(level_file)
    assert level.name == "Test Level"
    assert level.rows == 3
    assert level.cols == 4
    assert level.start == (0, 0)
    assert level.goal == (2, 3)
    assert 0 in level.bridges
    assert level.bridges[0].pos == (2, 2)
    assert (0, 1) in level.switches
    switch = level.switches[(0, 1)]
    assert switch.type == SwitchType.SOFT
    assert switch.effect.mode == EffectMode.TOGGLE
    assert 0 in switch.effect.bridges

def test_load_invalid_start(tmp_path):
    invalid_data = {
        "name": "Invalid",
        "grid": ["S#", "S#"]
    }
    level_file = tmp_path / "invalid_start.json"
    with open(level_file, "w") as f:
        json.dump(invalid_data, f)
    
    with pytest.raises(ValueError, match="exactly one start point"):
        load_level(level_file)

def test_load_invalid_char(tmp_path):
    invalid_data = {
        "name": "Invalid",
        "grid": ["SX", "G#"]
    }
    level_file = tmp_path / "invalid_char.json"
    with open(level_file, "w") as f:
        json.dump(invalid_data, f)
    
    with pytest.raises(ValueError, match="Invalid character 'X'"):
        load_level(level_file)

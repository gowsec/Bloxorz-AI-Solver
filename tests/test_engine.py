import pytest
from src.core.engine import Engine
from src.core.constants import Direction, Orientation, Outcome, Tile
from src.core.state import BlockPose, State
from src.core.move import Action
from src.utils.json_loader import load_level
import os

def test_engine_basic_movement():
    level_content = """
    {
        "name": "Test Level",
        "grid": [
            "S###",
            "####",
            "..G#"
        ]
    }
    """
    with open("temp_level.json", "w") as f:
        f.write(level_content)
    
    try:
        level = load_level("temp_level.json")
        engine = Engine(level)
        state = engine.initial_state()
        
        assert state.pose == BlockPose(0, 0, Orientation.STANDING)
        
        # Move right -> (0, 1) HORIZONTAL, occupies (0,1) and (0,2)
        next_state, outcome = engine.try_step(state, Action(Direction.RIGHT))
        assert outcome == Outcome.OK
        assert next_state.pose == BlockPose(0, 1, Orientation.HORIZONTAL)
        
    finally:
        if os.path.exists("temp_level.json"):
            os.remove("temp_level.json")

def test_engine_fragile_tile():
    level_content = """
    {
        "name": "Fragile Test",
        "grid": [
            "S#.",
            "F#.",
            "G#."
        ]
    }
    """
    with open("temp_fragile.json", "w") as f:
        f.write(level_content)
    
    try:
        level = load_level("temp_fragile.json")
        engine = Engine(level)
        state = engine.initial_state()
        
        # Move down to (1,0) VERTICAL, occupies (1,0) and (2,0)
        next_state, outcome = engine.try_step(state, Action(Direction.DOWN))
        assert outcome == Outcome.OK
        
        # Now move from (1,0) VERTICAL to (3,0) STANDING -> FELL (out of bounds)
        next_state_fall, outcome_fall = engine.try_step(next_state, Action(Direction.DOWN))
        assert outcome_fall == Outcome.FELL

        # Test fragile breaking
        level_content_3 = """
        {
            "name": "Fragile Test 3",
            "grid": [
                "####",
                "FSG#",
                "####"
            ]
        }
        """
        with open("temp_fragile_3.json", "w") as f: f.write(level_content_3)
        engine3 = Engine(load_level("temp_fragile_3.json"))
        
        # To stand on F at (1,0), we can start from HORIZONTAL (1,1)-(1,2) and move LEFT
        # (1,1) is S, (1,2) is G.
        # Wait, if we start at (1,1) STANDING, we move RIGHT to (1,2) HORIZONTAL (occupying 1,2 and 1,3)
        s3 = engine3.initial_state()
        s3_r, o3_r = engine3.try_step(s3, Action(Direction.RIGHT))
        assert o3_r == Outcome.OK
        
        # From (1,2) HORIZONTAL, move LEFT to (1,1) STANDING
        s3_l, o3_l = engine3.try_step(s3_r, Action(Direction.LEFT))
        assert o3_l == Outcome.OK
        
        # From (1,1) STANDING, move LEFT to (1,-1) HORIZONTAL... no.
        # We need to be HORIZONTAL (1,0)-(1,1) and move LEFT to be STANDING on (1,0).
        # To be HORIZONTAL (1,0)-(1,1), we move RIGHT from (1,-1) STANDING... no.
        
        # Let's just use a state with Orientation.HORIZONTAL at (1,1)
        s_horiz = State(BlockPose(1, 1, Orientation.HORIZONTAL), 0) # occupies (1,1) and (1,2)
        # Move LEFT -> STANDING on (1,0)
        s_final, o_final = engine3.try_step(s_horiz, Action(Direction.LEFT))
        assert o_final == Outcome.FRAGILE_BROKE
        
    finally:
        for f in ["temp_fragile.json", "temp_fragile_3.json"]:
            if os.path.exists(f): os.remove(f)

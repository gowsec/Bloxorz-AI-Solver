"""Test cho utils/json_loader.py theo architecture.md mục 7.3.

Nguyên tắc: mỗi luật có ít nhất một ca lỗi, và MỖI CA LỖI CHỈ VI PHẠM ĐÚNG MỘT LUẬT. Các ca lỗi
đều sinh từ cùng một màn hợp lệ (VALID) bằng một thay đổi nhỏ, nên test không phụ thuộc vào thứ tự
kiểm tra của loader. Luật 12 (split_targets trùng công tắc) chưa test vì nhóm chưa chốt có cấm hay không.
"""
import copy
import json
from pathlib import Path

import pytest

from src.core.board import EffectMode, SwitchType
from src.core.engine import Engine
from src.solvers.astar import AStarSolver
from src.solvers.base_solver import STATUS_NO_SOLUTION, STATUS_SOLVED, STATUS_TIMEOUT
from src.utils.json_loader import load_level

LEVELS_DIR = Path(__file__).resolve().parent.parent / "levels"
LEVEL_FILES = sorted(LEVELS_DIR.glob("level*.json"))
# kế hoạch: level01..level10 (B) và level11 trở đi (C)
MIN_LEVEL_FILES = 10
SOLVE_TIME_LIMIT = 20.0

# Màn hợp lệ dùng đủ mọi tính năng: ô dễ vỡ, 2 cầu, công tắc soft/heavy/split.
VALID = {
    "name": "valid",
    "grid": [
        "S#####",
        "######",
        "#.##.#",
        "###F##",
        "####G#",
    ],
    "bridges": [
        {"id": 0, "pos": [2, 1], "initial_open": False},
        {"id": 1, "pos": [2, 4], "initial_open": True},
    ],
    "switches": [
        {"pos": [0, 2], "type": "soft", "effect": {
            "mode": "toggle", "bridges": [0]}},
        {"pos": [1, 3], "type": "heavy", "effect": {
            "mode": "set_open", "bridges": [0]}},
        {"pos": [3, 0], "type": "split", "split_targets": [[4, 1], [1, 5]]},
    ],
}


def write_level(tmp_path, data, name="level.json"):
    path = tmp_path / name
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def corridor(n_bridges):
    """Một hàng S, n cầu, G: dùng để thử giới hạn số cầu (luật 7)."""
    return {
        "name": "corridor",
        "grid": ["S" + "." * n_bridges + "G"],
        "bridges": [{"id": i, "pos": [0, i + 1], "initial_open": True} for i in range(n_bridges)],
        "switches": [],
    }


def replace_all(data, new):
    data.clear()
    data.update(new)


# (id, luật bị vi phạm, hàm biến đổi màn hợp lệ)
INVALID_CASES = [
    # Luật 1: đúng một S và một G
    ("no-start", 1, lambda d: d["grid"].__setitem__(0, "######")),
    ("two-starts", 1, lambda d: d["grid"].__setitem__(0, "SS####")),
    ("no-goal", 1, lambda d: d["grid"].__setitem__(4, "######")),
    ("two-goals", 1, lambda d: d["grid"].__setitem__(4, "####GG")),
    # Luật 2: grid hợp lệ (hàng cùng độ dài, ký tự hợp lệ, không rỗng)
    ("unequal-row-lengths", 2, lambda d: d["grid"].__setitem__(3, "###F#")),
    ("invalid-character", 2, lambda d: d["grid"].__setitem__(1, "X#####")),
    # Luật 3: cầu (id duy nhất và liên tục từ 0, vị trí trong bảng và trên ô '.')
    ("duplicate-bridge-ids", 3, lambda d: d["bridges"][1].update(id=0)),
    ("bridge-ids-not-contiguous", 3, lambda d: d["bridges"][1].update(id=2)),
    ("bridge-out-of-bounds", 3, lambda d: d["bridges"][1].update(pos=[9, 9])),
    ("bridge-not-on-void-tile", 3,
     lambda d: d["bridges"][1].update(pos=[1, 1])),
    # Luật 4: công tắc (trong bảng, trên ô '#', không trùng cầu hoặc công tắc khác)
    ("switch-on-bridge-cell", 4,
     lambda d: d["switches"][0].update(pos=[2, 1])),
    ("switch-on-fragile-tile", 4,
     lambda d: d["switches"][1].update(pos=[3, 3])),
    ("switch-on-goal", 4, lambda d: d["switches"][1].update(pos=[4, 4])),
    ("switch-on-start", 4, lambda d: d["switches"][1].update(pos=[0, 0])),
    ("switch-out-of-bounds", 4, lambda d: d["switches"][1].update(pos=[9, 9])),
    ("two-switches-same-cell", 4,
     lambda d: d["switches"][1].update(pos=[0, 2])),
    # Luật 5: effect chỉ tham chiếu cầu tồn tại
    ("effect-refers-to-missing-bridge", 5,
     lambda d: d["switches"][0]["effect"].update(bridges=[5])),
    # Luật 6: split_targets (2 ô sàn khác nhau, không kề nhau)
    ("split-targets-same-cell", 6,
     lambda d: d["switches"][2].update(split_targets=[[4, 1], [4, 1]])),
    ("split-targets-adjacent", 6,
     lambda d: d["switches"][2].update(split_targets=[[4, 1], [4, 2]])),
    ("split-target-on-bridge-cell", 6,
     lambda d: d["switches"][2].update(split_targets=[[4, 1], [2, 1]])),
    ("split-target-out-of-bounds", 6,
     lambda d: d["switches"][2].update(split_targets=[[4, 1], [9, 9]])),
    ("split-targets-wrong-count", 6,
     lambda d: d["switches"][2].update(split_targets=[[4, 1]])),
    # Luật 7: tối đa 62 cầu
    ("too-many-bridges", 7, lambda d: replace_all(d, corridor(63))),
    # Luật 8: type và mode phải được hỗ trợ
    ("unknown-switch-type", 8,
     lambda d: d["switches"][0].update(type="medium")),
    ("unknown-effect-mode", 8,
     lambda d: d["switches"][0]["effect"].update(mode="swap")),
    # Luật 9: soft/heavy cần effect hợp lệ, split cần split_targets
    ("soft-without-effect", 9, lambda d: d["switches"][0].pop("effect")),
    ("heavy-without-effect", 9, lambda d: d["switches"][1].pop("effect")),
    ("effect-without-bridges", 9,
     lambda d: d["switches"][0]["effect"].update(bridges=[])),
    ("split-without-targets", 9,
     lambda d: d["switches"][2].pop("split_targets")),
    # Luật 11: không có hai cầu trên cùng một ô
    ("two-bridges-same-cell", 11,
     lambda d: d["bridges"][1].update(pos=[2, 1])),
]
# Luật 2 còn một ca đặc biệt: grid rỗng (đồng thời không có S và G nên cũng vi phạm luật 1).
EMPTY_GRID = {"name": "empty", "grid": []}


def mutated(change):
    data = copy.deepcopy(VALID)
    change(data)
    return data


# ----------------------------------------------------------------------------------------
# Màn hợp lệ nạp đúng
# ----------------------------------------------------------------------------------------
def test_valid_level_loads_with_expected_values(tmp_path):
    level = load_level(write_level(tmp_path, VALID))

    assert (level.name, level.rows, level.cols) == ("valid", 5, 6)
    assert level.start == (0, 0) and level.goal == (4, 4)
    assert level.bridges[0].pos == (
        2, 1) and level.bridges[0].initial_open is False
    assert level.bridges[1].pos == (
        2, 4) and level.bridges[1].initial_open is True
    assert level.bridge_at == {(2, 1): 0, (2, 4): 1}

    soft, heavy, split = (level.switches[p] for p in [(0, 2), (1, 3), (3, 0)])
    assert soft.type is SwitchType.SOFT and soft.effect.mode is EffectMode.TOGGLE
    assert soft.effect.bridges == (0,) and soft.effect.mask == 0b1
    assert heavy.type is SwitchType.HEAVY and heavy.effect.mode is EffectMode.SET_OPEN
    assert split.type is SwitchType.SPLIT and split.effect is None


def test_split_targets_are_tuples_so_states_stay_hashable(tmp_path):
    split = load_level(write_level(tmp_path, VALID)).switches[(3, 0)]

    assert split.split_targets == ((4, 1), (1, 5))
    # list lồng nhau sẽ ném TypeError khi State chứa chúng bị đưa vào set
    hash(split.split_targets)


def test_missing_bridges_and_switches_default_to_empty(tmp_path):
    level = load_level(write_level(
        tmp_path, {"name": "tiny", "grid": ["S#", "#G"]}))

    assert level.bridges == {} and level.bridge_at == {} and level.switches == {}


def test_exactly_62_bridges_is_allowed(tmp_path):
    assert len(load_level(write_level(tmp_path, corridor(62))).bridges) == 62


# ----------------------------------------------------------------------------------------
# Màn lỗi bị từ chối
# ----------------------------------------------------------------------------------------
@pytest.mark.parametrize("case_id, rule, change", INVALID_CASES, ids=[c[0] for c in INVALID_CASES])
def test_invalid_level_is_rejected(tmp_path, case_id, rule, change):
    path = write_level(tmp_path, mutated(change))

    with pytest.raises(ValueError):
        load_level(path)


def test_empty_grid_is_rejected(tmp_path):
    with pytest.raises(ValueError):
        load_level(write_level(tmp_path, EMPTY_GRID))


def test_error_message_names_the_file(tmp_path):
    """Mục 7.3: loader phải báo lỗi rõ ràng, nêu tên file."""
    path = write_level(tmp_path, mutated(
        INVALID_CASES[0][2]), name="my_broken_level.json")

    with pytest.raises(ValueError) as error:
        load_level(path)

    assert "my_broken_level.json" in str(error.value)


# ----------------------------------------------------------------------------------------
# Các file màn thật trong levels/
# ----------------------------------------------------------------------------------------
def test_enough_level_files_exist():
    assert len(
        LEVEL_FILES) >= MIN_LEVEL_FILES, f"cần ít nhất {MIN_LEVEL_FILES} màn trong {LEVELS_DIR}"


@pytest.mark.parametrize("path", LEVEL_FILES, ids=lambda p: p.name)
def test_level_file_loads(path):
    assert load_level(path).name


@pytest.mark.parametrize("path", LEVEL_FILES, ids=lambda p: p.name)
def test_level_file_has_a_solution(path):
    result = AStarSolver(Engine(load_level(path)),
                         time_limit=SOLVE_TIME_LIMIT).solve(measure_memory=False)

    if result.status == STATUS_TIMEOUT:
        pytest.skip(f"A* chưa giải xong trong {SOLVE_TIME_LIMIT} giây")
    assert result.status != STATUS_NO_SOLUTION, f"{path.name} vô nghiệm"
    assert result.status == STATUS_SOLVED

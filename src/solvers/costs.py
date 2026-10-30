"""Hàm chi phí dùng chung cho UCS và A*.

Mô hình chi phí (rủi ro):

    chi phí của một nước đi = BASE_COST
                              + FRAGILE_PENALTY  nếu khối (nguyên) kết thúc nước đi
                                                 với BẤT KỲ ô nào nằm trên ô dễ vỡ

Giải thích (dùng cho báo cáo):
* Mỗi nước lăn tốn 1 đơn vị: đó là công sức cơ bản của người chơi.
* Ô dễ vỡ chỉ an toàn khi khối nằm; chỉ cần một nước đi sai là khối đứng lên đó và rơi.
  Vì vậy đường đi qua ô dễ vỡ được coi là "rủi ro" và bị cộng thêm FRAGILE_PENALTY,
  khiến UCS/A* ưu tiên đường vòng an toàn nếu nó không dài hơn quá FRAGILE_PENALTY nước.
* Khối lập phương (sau khi tách) không làm vỡ ô dễ vỡ nên không bị phạt.
* KHÔNG giảm chi phí cho nước đi kích hoạt công tắc (dù đề bài gợi ý "rẻ"): mọi
  chi phí < 1 sẽ kéo C_MIN xuống và làm heuristic yếu đi tương ứng. Cần giảm thì
  chỉnh BASE_COST/C_MIN ở đây, heuristics.py tự cập nhật theo C_MIN.

Ràng buộc mà heuristics.py DỰA VÀO (đổi là phải rà lại chứng minh trong docs):
  1. step_cost >= C_MIN > 0 với mọi nước đi.
  2. step_cost chỉ phụ thuộc vào TƯ THẾ MỚI (next_state.pose) và địa hình tĩnh của màn,
     không phụ thuộc vào trạng thái cầu, hành động hay trạng thái trước.
"""
from __future__ import annotations

from src.core.constants import Tile
from src.core.state import BlockPose, cells

BASE_COST = 1.0
FRAGILE_PENALTY = 1.0
FRAGILE_TILE = Tile.FRAGILE  # ký tự ô dễ vỡ trong level.terrain (lấy từ core/constants.py)

# Chi phí nhỏ nhất của một nước đi. Vì phạt chỉ cộng thêm (>= 0) nên C_MIN = BASE_COST.
C_MIN = BASE_COST

assert BASE_COST > 0, "BASE_COST phải dương để UCS/A* dừng được"
assert FRAGILE_PENALTY >= 0, "Phạt âm sẽ làm C_MIN nhỏ hơn BASE_COST"


def touches_fragile(level, pose) -> bool:
    """True nếu có ô nào của pose nằm trên ô dễ vỡ."""
    return any(level.terrain[r][c] == FRAGILE_TILE for r, c in cells(pose))


def roll_cost(level, pose) -> float:
    """Chi phí của nước đi kết thúc ở `pose` (chỉ phụ thuộc pose và địa hình tĩnh)."""
    if isinstance(pose, BlockPose) and touches_fragile(level, pose):
        return BASE_COST + FRAGILE_PENALTY
    return BASE_COST


def step_cost(engine, state, action, next_state) -> float:
    """Chi phí chuyển từ `state` sang `next_state` bằng `action` (interface theo mục 6.5)."""
    return roll_cost(engine.level, next_state.pose)

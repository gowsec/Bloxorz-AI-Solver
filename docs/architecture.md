# Kiến trúc hệ thống Bloxorz AI Solver

> Trạng thái triển khai bước 1: xem `milestone01.md`. Level hiện có name,
> terrain, start, goal; rows/cols là property. `Level.from_grid` tạo level
> viết tay tạm thời. Các interface đầy đủ dưới đây là đích triển khai tiếp theo.

> **Phiên bản:** 1.0 (bản chốt interface)
> **Người duyệt thay đổi:** Minh Quang (Team Lead). Mọi thay đổi ở các interface trong tài liệu này phải qua Pull Request và được Minh Quang duyệt, vì chúng ảnh hưởng đến cả bốn solver, GUI và benchmark.

---

## 1. Mục tiêu và nguyên tắc

1. **Tách lớp:** `core` + `mechanics` (luật chơi) không biết gì về `gui` và `solvers`. `solvers` chỉ nói chuyện với engine qua interface ở mục 5. `gui` chỉ nói chuyện với engine và solver qua interface, không chứa luật.
2. **Solver chạy được không cần pygame:** benchmark chạy hàng loạt ở chế độ headless.
3. **`State` bất biến và hashable:** dùng được trực tiếp làm khóa trong `set` / `dict` (visited, g-cost).
4. **Một nguồn sự thật:** luật nước đi chỉ nằm trong `engine.py` (và các `mechanics/*` do engine gọi). Nơi khác không tự cài lại luật.
5. **Một nguồn chi phí:** `costs.py` dùng chung cho UCS và A\*, `heuristics.py` phải admissible theo đúng `costs.py`.

```
Level JSON ──► json_loader ──► Level ──► Engine ◄── Solvers (BFS/DFS/UCS/A*)
                                           ▲
                                           └────── GUI (chơi tay, replay lời giải)
```

---

## 2. Quy ước chung

### 2.1. Tọa độ

- `Pos = tuple[int, int]` là `(r, c)`: `r` là hàng (tăng khi đi xuống), `c` là cột (tăng khi đi sang phải). Gốc `(0, 0)` là góc trên trái.

### 2.2. Hướng đi

```python
class Direction(IntEnum):
    UP = 0      # (-1,  0)
    DOWN = 1    # (+1,  0)
    LEFT = 2    # ( 0, -1)
    RIGHT = 3   # ( 0, +1)
```

### 2.3. Tư thế khối

```python
class Orientation(IntEnum):
    STANDING = 0     # chiếm (r, c)
    HORIZONTAL = 1   # chiếm (r, c) và (r, c+1)
    VERTICAL = 2     # chiếm (r, c) và (r+1, c)
```

Với khối nằm, `(r, c)` luôn là **ô góc trên trái** của khối (ô có `r` nhỏ nhất, `c` nhỏ nhất).

### 2.4. Loại ô

| Ký tự trong grid | Loại ô | Ý nghĩa |
|---|---|---|
| `.` | VOID | Không có sàn, đặt chân lên là rơi |
| `#` | FLOOR | Sàn thường |
| `S` | START | Sàn thường, khối bắt đầu **đứng** ở đây |
| `G` | GOAL | Ô đích (xem luật thắng ở mục 4.5) |
| `F` | FRAGILE | Ô dễ vỡ |

Cầu và công tắc **không** mã hóa bằng ký tự trong grid mà khai báo trong danh sách riêng (mục 7). Ô công tắc là sàn thường trong grid (`#`). Ô cầu để `.` trong grid, trạng thái thật do `bridges` quyết định.

---

## 3. Mô hình trạng thái (`core/state.py`)

### 3.1. Định nghĩa

Trạng thái có hai chế độ: khối nguyên 1×1×2, hoặc đã tách thành hai khối lập phương 1×1×1.

```python
Pos = tuple[int, int]

@dataclass(frozen=True, slots=True)
class BlockPose:
    r: int
    c: int
    orient: Orientation

@dataclass(frozen=True, slots=True)
class SplitPose:
    a: Pos            # khối lập phương số 0
    b: Pos            # khối lập phương số 1

@dataclass(frozen=True, slots=True)
class State:
    pose: BlockPose | SplitPose
    bridges: int      # bitmask: bit i = 1 nghĩa là cầu có id i đang MỞ
```

### 3.2. Quy tắc

- `State` **bất biến** (`frozen=True`) nên tự có `__hash__` và `__eq__`. Cấm sửa state tại chỗ, mỗi nước đi tạo state mới.
- **Mọi thứ ảnh hưởng đến tương lai phải nằm trong State.** Hai state cùng vị trí nhưng khác `bridges` là hai state khác nhau.
- Ô dễ vỡ **không** cần lưu trong state: ô dễ vỡ bị phá đồng nghĩa với việc khối rơi, tức là thua, nên không có trạng thái "ô đã vỡ" nào tiếp tục được.
- Công tắc *permanent* cũng không cần cờ "đã dùng": kích hoạt lần nữa chỉ đặt lại cùng giá trị nên không đổi gì (xem mục 4.4).
- Khối **không** lưu "khối nào đang được điều khiển". Ở chế độ tách, hành động tự chỉ rõ khối nào di chuyển (mục 5.2). Việc này giảm số trạng thái và bỏ hành động "đổi khối". Phím Space trong GUI chỉ là trạng thái của giao diện, không phải của bài toán tìm kiếm.
- Khi cần chuẩn hóa để giảm trùng lặp (`a, b` và `b, a` là cùng cấu hình), có thể sắp xếp `(a, b)` nhưng khi đó GUI không theo dõi được danh tính từng khối. Mặc định: **không** chuẩn hóa.

### 3.3. Hàm tiện ích bắt buộc

```python
def cells(pose: BlockPose | SplitPose) -> tuple[Pos, ...]:
    """Các ô mà pose đang chiếm (1 hoặc 2 ô)."""

def is_split(state: State) -> bool: ...
```

---

## 4. Luật chơi (`core/move.py`, `core/engine.py`, `mechanics/*`)

### 4.1. Bảng chuyển tư thế (khối nguyên)

Đây là bảng quan trọng nhất, **B phải viết unit test cho toàn bộ 12 trường hợp chuyển tư thế**. Ký hiệu `(r, c)` là ô góc trên trái của pose hiện tại.

| Tư thế hiện tại | UP | DOWN | LEFT | RIGHT |
|---|---|---|---|---|
| **STANDING** `(r,c)` | VERTICAL `(r-2, c)` | VERTICAL `(r+1, c)` | HORIZONTAL `(r, c-2)` | HORIZONTAL `(r, c+1)` |
| **HORIZONTAL** `(r,c)` | HORIZONTAL `(r-1, c)` | HORIZONTAL `(r+1, c)` | STANDING `(r, c-1)` | STANDING `(r, c+2)` |
| **VERTICAL** `(r,c)` | STANDING `(r-1, c)` | STANDING `(r+2, c)` | VERTICAL `(r, c-1)` | VERTICAL `(r, c+1)` |

Ví dụ kiểm tra: khối đứng ở `(3,3)` lăn RIGHT thì nằm ngang chiếm `(3,4)` và `(3,5)`, tức `HORIZONTAL (3,4)`. Lăn tiếp RIGHT thì đứng ở `(3,6)`, tức `STANDING (3,6)`.

### 4.2. Di chuyển khi tách khối

Khối lập phương di chuyển một ô theo hướng chọn: `(r, c) → (r+dr, c+dc)`. Hai khối **không được chiếm cùng một ô**.

### 4.3. Điều kiện nâng đỡ (support)

Một pose là hợp lệ khi **mọi ô nó chiếm** thỏa tất cả:

1. Nằm trong bảng (không ra ngoài).
2. Không phải ô VOID.
3. Không phải ô cầu đang đóng (cầu đóng giống ô trống, cầu mở giống sàn thường).
4. Nếu là ô FRAGILE: khối **không** ở tư thế STANDING. Khối nằm vắt qua ô dễ vỡ thì an toàn.

Quy ước cần cả nhóm xác nhận (mặc định ghi ở đây): **khối lập phương 1×1×1 không làm vỡ ô dễ vỡ** (trọng lượng nhỏ).

### 4.4. Công tắc

Công tắc được kích hoạt **chỉ bởi các ô mà phần tử vừa di chuyển đáp xuống** sau nước đi đó. Ở chế độ tách, khối đứng yên không kích hoạt lại.

| Loại | Điều kiện kích hoạt |
|---|---|
| `soft` | Bất kỳ phần nào của khối hoặc khối lập phương đáp lên ô công tắc, mọi tư thế |
| `heavy` | Chỉ khi khối nguyên ở tư thế **STANDING** trên ô đó. Khối lập phương **không** kích hoạt được |
| `split` | Chỉ khi khối nguyên **STANDING** trên ô đó. Khối được dịch chuyển đến hai vị trí định sẵn `split_targets` và tách thành hai khối lập phương. Khối lập phương không kích hoạt được |

Tác động lên cầu (áp dụng cho `soft` và `heavy`) khai báo bằng `effect`:

| `mode` | Hành vi |
|---|---|
| `toggle` | Mỗi lần kích hoạt đảo trạng thái đóng/mở của các cầu liên kết |
| `set_open` | Đặt cố định các cầu liên kết thành **mở** (kích hoạt lại không đổi gì) |
| `set_close` | Đặt cố định các cầu liên kết thành **đóng** |

Công tắc `split` **chỉ tách khối**, không tác động lên cầu (đơn giản hóa).

### 4.5. Ghép khối và thắng

- **Ghép (merge):** sau một nước đi ở chế độ tách, nếu hai khối lập phương nằm ở hai ô **kề cạnh** (4 hướng) thì tự động ghép lại thành khối nằm: cùng hàng thì `HORIZONTAL`, cùng cột thì `VERTICAL`, với `(r, c)` là ô góc trên trái. Việc ghép **không** kích hoạt lại công tắc nào.
- **Thắng:** state là goal khi `pose` là `BlockPose` có `orient == STANDING` và `(r, c) == goal`. Khối nằm vắt qua ô đích không thắng. Ở chế độ tách, không thể thắng. Với khối lập phương, ô đích chỉ là sàn thường.
- State goal là **trạng thái kết thúc**: engine không sinh nước đi từ nó.

### 4.6. Thứ tự xử lý của `engine.step` (cố định)

Với `step(state, action)`, engine thực hiện đúng thứ tự sau, và **dừng trả về lỗi ngay khi một bước thất bại**:

0. **Kiểm tra Action**. Nếu khối nguyên nhưng `cube != None`, hoặc đang tách nhưng cube không thuộc `{0, 1}`, trả về `(None, Outcome.INVALID_ACTION)`.
1. **Tính pose mới** bằng bảng ở 4.1 (hoặc di chuyển khối lập phương, 4.2).
2. **Kiểm tra nâng đỡ** (4.3) cho pose mới, dùng `bridges` **hiện tại**. Thất bại: `FELL` hoặc `FRAGILE_BROKE`.
3. **Kích hoạt công tắc** (4.4) ở các ô vừa đáp xuống, tính `bridges` mới.
4. **Kiểm tra nâng đỡ lần hai** với `bridges` mới (cầu vừa đóng dưới chân khối thì khối rơi). Thất bại: `FELL`.
5. **Tách khối** nếu vừa đứng trên công tắc `split`: thay pose bằng `SplitPose(split_targets)`. Hai vị trí đích được loader đảm bảo là sàn hợp lệ và không kề nhau.
6. **Ghép khối** nếu đang ở chế độ tách và hai khối kề cạnh (4.5).
7. **Trả về** state mới. Kiểm tra goal do `is_goal` đảm nhiệm.

Thứ tự này phải được test (`tests/test_mechanics.py`), nhất là bước 4 (đóng cầu dưới chân) và bước 5-6 (tách rồi ghép).

---

## 5. Interface của Engine (`core/engine.py`)

### 5.1. Chữ ký

```python
class Engine:
    def __init__(self, level: Level): ...

    def initial_state(self) -> State:
        """Khối STANDING tại level.start, bridges theo level.bridges[*].initial_open."""

    def get_actions(self, state: State) -> list[Action]:
        """Các hành động có thể thử ở state này (chưa lọc hợp lệ).
        Rỗng nếu state là goal."""

    def try_step(self, state: State, action: Action) -> tuple[State | None, Outcome]:
        """Áp dụng action. Trả (state_mới, Outcome.OK) hoặc (None, lý do thất bại).
        GUI dùng hàm này để hiển thị 'rơi khỏi bàn' / 'ô dễ vỡ vỡ'."""

    def step(self, state: State, action: Action) -> State | None:
        """Giống try_step nhưng chỉ trả state hoặc None nếu nước đi không hợp lệ."""

    def get_successors(self, state: State) -> list[tuple[Action, State]]:
        """Chỉ các nước đi HỢP LỆ. Đây là hàm duy nhất solver được gọi để mở rộng node."""

    def is_goal(self, state: State) -> bool: ...
```

### 5.2. Action

```python
@dataclass(frozen=True, slots=True)
class Action:
    direction: Direction
    cube: int | None = None   # None khi khối nguyên; 0 hoặc 1 khi đang tách
```

- Khối nguyên: 4 hành động `(direction, None)`.
- Đang tách: 8 hành động `(direction, 0|1)`.

### 5.3. Outcome

```python
class Outcome(Enum):
    OK = auto()
    FELL = auto()            # ra ngoài bảng, ô trống, cầu đóng
    FRAGILE_BROKE = auto()   # khối đứng lên ô dễ vỡ
    BLOCKED = auto()         # hai khối lập phương chồng lên nhau
    INVALID_ACTION = auto()  # Action không phù hợp với trạng thái hiện tại
```

### 5.4. Ràng buộc

- Engine là **thuần hàm** theo `(state, action)`: không giữ trạng thái thay đổi bên trong. Nhiều solver dùng chung một `Engine`.
- `get_successors` luôn trả cùng thứ tự hành động (UP, DOWN, LEFT, RIGHT, và khối 0 trước khối 1) để kết quả tái lập được.

---

## 6. Interface của Solver (`solvers/`)

### 6.1. `SolverResult` (`solvers/result.py`)

```python
@dataclass
class SolverResult:
    algorithm: str
    path: list[Action]            # rỗng nếu không tìm thấy
    states: list[State]           # dãy state từ đầu đến đích, GUI dùng để replay
    solution_length: int          # len(path), số nước đi
    total_cost: float             # tổng chi phí theo costs.py
    expanded_nodes: int
    generated_nodes: int
    search_time: float            # giây
    peak_memory: int              # byte
    status: Literal[
        "solved",                 # Tìm được lời giải
        "no_solution",            # Đã tìm hết không gian trạng thái nhưng không có lời giải
        "timeout",                # Vượt thời gian cho phép
        "node_limit"              # Vượt số node cho phép
    ]
```

- Khi `status == "solved"`: `len(states) == len(path) + 1` (gồm trạng thái đầu và cuối).
- Các trường hợp còn lại: `path=[]`, `states=[]`, `solution_length=0`, `total_cost=float("inf")`.
- BaseSolver.solve() phải tạo một đối tượng Stats mới cho mỗi lần gọi, đảm bảo các chỉ số thống kê không bị cộng dồn giữa những lần chạy.

```python
class SearchLimitExceeded(Exception):
    def __init__(self, status: str):   # "timeout" hoặc "node_limit"
        self.status = status

@dataclass
class Stats:
    expanded: int = 0
    generated: int = 0
    deadline: float | None = None      # thời điểm perf_counter, đặt bởi solve()
    node_limit: int | None = None
    def check(self): ...               # raise SearchLimitExceeded nếu vượt
``` 
### 6.2. `BaseSolver` (`solvers/base_solver.py`)

```python
class BaseSolver(ABC):
    name: str

    def solve(self,
        engine: Engine,
        time_limit: float | None = None,
        node_limit: int | None = None
    ) -> SolverResult:
        """Template method: bắt đầu đo, gọi _search, dừng đo, đóng gói SolverResult."""

    @abstractmethod
    def _search(self, engine: Engine, start: State, stats: Stats) -> list[Action] | None:
        """Cài đặt thuật toán. Gọi stats.expanded += 1 mỗi lần mở rộng node."""
```

- `solve()` đặt `stats.deadline` và `stats.node_limit` trước khi gọi `_search`, và bắt `SearchLimitExceeded` để gán `status`.
- `_search` phải gọi `stats.check()` mỗi lần mở rộng node.
- `_search` trả `None` **chỉ** khi đã duyệt hết không gian trạng thái (tức `status = "no_solution"`).

### 6.3. Định nghĩa thống nhất cho thực nghiệm

Để so sánh công bằng giữa 4 thuật toán, **tất cả phải theo cùng định nghĩa**:

| Chỉ số | Định nghĩa |
|---|---|
| **Expanded node** | Mỗi lần node được lấy ra khỏi frontier (không phải goal) và `get_successors` được gọi trên nó |
| **Generated node** | Mỗi state được đưa vào frontier |
| **Goal test** | Thực hiện khi **lấy node ra khỏi frontier** (bắt buộc với UCS, A\* để đảm bảo tối ưu; dùng chung cho BFS, DFS để thống nhất) |
| **Solution length** | `len(path)`, số hành động |
| **Search time** | `time.perf_counter()`, không tính thời gian nạp màn |
| **Peak memory** | `tracemalloc.get_traced_memory()[1]` |

**Lưu ý đo:** `tracemalloc` làm chương trình chạy chậm đáng kể. Vì vậy `benchmark.py` phải chạy **hai lượt riêng**: một lượt chỉ đo thời gian, một lượt đo bộ nhớ, và chạy thời gian nhiều lần lấy trung vị. Bộ nhớ đo bằng `tracemalloc` là **peak Python-tracked memory**, không phải toàn bộ RAM của tiến trình.

### 6.4. Xử lý trạng thái lặp

| Thuật toán | Cách xử lý |
|---|---|
| BFS | `visited: set[State]`, đánh dấu khi đưa vào frontier |
| DFS | `visited: set[State]` toàn cục. Nếu dùng **IDS**: chỉ chặn chu trình trên nhánh hiện tại, hoặc lưu độ sâu nhỏ nhất đã thấy của mỗi state |
| UCS | `best_g: dict[State, float]`, bỏ qua mục cũ trong heap (lazy deletion) |
| A\* | Như UCS, kèm `h`. Nếu heuristic nhất quán thì không cần mở lại node đã đóng |

***Quy ước heap cho UCS và A\*:*** Mỗi phần tử trong priority queue có dạng (priority, counter, node), trong đó counter là số thứ tự tăng dần, duy nhất cho mỗi lần thêm node. Không sử dụng (priority, state) vì State không hỗ trợ so sánh thứ tự. Quy ước này cũng giúp kết quả chạy có tính tái lập.

### 6.5. Hàm chi phí (`solvers/costs.py`) và heuristic (`solvers/heuristics.py`)

```python
def step_cost(engine: Engine, state: State, action: Action, next_state: State) -> float: ...
def heuristic(engine: Engine, state: State) -> float: ...
```

**Ràng buộc bắt buộc:**

- `step_cost > 0` với mọi nước đi, và có hằng `C_MIN = min(step_cost)` công bố trong `costs.py`.
- Heuristic phải **admissible theo `step_cost`**: `h(s) ≤` chi phí tối ưu thật từ `s` đến goal. Cách an toàn: `h(s) = C_MIN × (cận dưới số nước lăn còn lại)`.
- Khuyến nghị làm heuristic **consistent** để A\* không phải mở lại node.
- Khi đổi `costs.py` thì **phải rà lại** chứng minh heuristic. Hai file này luôn được sửa cùng một PR.

Gợi ý khởi điểm để D và A thảo luận (chưa chốt):

- Chi phí: 1 mỗi nước đi; +1 nếu pose mới có ô dễ vỡ; chỉ 0.5 nếu nước đi kích hoạt công tắc. Khi đó `C_MIN = 0.5`.
- Cận dưới số nước lăn: mỗi lần lăn, tâm khối dịch tối đa **1,5 ô** theo một trục, nên số lăn tối thiểu từ tâm hiện tại đến tâm của khối đứng ở ô đích là `⌈Manhattan(tâm khối, đích) / 1.5⌉`. Ở chế độ tách, dùng `h = 0` cho đến khi có cận dưới được chứng minh.

---

## 7. Định dạng file màn chơi (`levels/*.json`)

Mỗi màn là **một file JSON**.

### 7.1. Ví dụ

```json
{
  "name": "Level 01",
  "grid": [
    "####....",
    "S###F###",
    "####..#G"
  ],
  "bridges": [
    { "id": 0, "pos": [2, 4], "initial_open": false },
    { "id": 1, "pos": [2, 5], "initial_open": false }
  ],
  "switches": [
    {
      "pos": [0, 2],
      "type": "soft",
      "effect": { "mode": "toggle", "bridges": [0, 1] }
    }
  ]
}
```

Ví dụ này chỉ minh họa định dạng, chưa chắc có lời giải. Mẫu khai báo hai loại công tắc còn lại:

```json
{ "pos": [1, 1], "type": "heavy",
  "effect": { "mode": "set_open", "bridges": [0] } }

{ "pos": [1, 2], "type": "split",
  "split_targets": [[0, 0], [2, 3]] }
```

### 7.2. Trường dữ liệu

| Trường | Bắt buộc | Mô tả |
|---|---|---|
| `name` | có | Tên màn |
| `grid` | có | Danh sách chuỗi, mọi hàng cùng độ dài. Ký tự: `. # S G F` |
| `bridges` | không | `id` (số nguyên từ 0, liên tục), `pos`, `initial_open` |
| `switches` | không | `pos`, `type` (`soft`/`heavy`/`split`), `effect` (với soft, heavy), `split_targets` (với split) |

### 7.3. Các điều kiện kiểm tra khi nạp (`json_loader.py`)

Loader phải **báo lỗi rõ ràng** (nêu tên file và vị trí) nếu vi phạm:

1. Đúng **một** ô `S` và đúng **một** ô `G`.
2. Mọi hàng của `grid` cùng độ dài, chỉ chứa ký tự hợp lệ, không được rỗng.
3. `id` cầu duy nhất, liên tục từ 0; vị trí cầu nằm trong bảng và ở grid là `.`.
4. Vị trí công tắc nằm trong bảng, là `#` (không phải `.`, `F`, `G`, `S`, cầu); không có hai công tắc cùng ô.
5. `effect.bridges` chỉ tham chiếu `id` cầu tồn tại.
6. `split_targets` gồm đúng hai vị trí khác nhau, **không kề cạnh**, đều là sàn hợp lệ (không phải VOID, cầu, hay ô dễ vỡ... trừ khi nhóm chốt cho phép).
7. Số cầu không vượt quá 62 (để dùng bitmask `int` gọn).
8. Type, mode phải thuộc những giá trị được hỗ trợ.
9. Soft/heavy phải có effect hợp lệ; split phải có split_targets hợp lệ.
10. Bridges, switches nếu không khai báo thì mặc định là danh sách rỗng.
11. Không được khai báo nhiều cầu trên cùng một ô.
12. `split_targets` không trùng bất kỳ công tắc nào, nếu nhóm chọn quy tắc cấm này.

### 7.4. Kiểu dữ liệu sau khi nạp

Các kiểu dưới đây đặt trong `core/board.py` (do B phụ trách). `json_loader` là nơi duy nhất tạo ra chúng, và đã kiểm tra mọi điều kiện ở 7.3. Engine và các mechanics (do C phụ trách) được phép **tin rằng dữ liệu đã hợp lệ**, không kiểm tra lại.

#### Kiểu liệt kê

```python
class SwitchType(Enum):
    SOFT = "soft"
    HEAVY = "heavy"
    SPLIT = "split"

class EffectMode(Enum):
    TOGGLE = "toggle"        # đảo đóng/mở
    SET_OPEN = "set_open"    # đặt cố định thành mở
    SET_CLOSE = "set_close"  # đặt cố định thành đóng
```

Giá trị chuỗi của `Enum` trùng đúng với chuỗi trong file JSON, nên loader chuyển bằng `SwitchType(raw)` và `EffectMode(raw)`. Nếu `ValueError` thì báo lỗi theo luật số 8 ở 7.3.

#### Cầu

```python
@dataclass(frozen=True, slots=True)
class Bridge:
    pos: Pos
    initial_open: bool       # trạng thái ban đầu, từ trường "initial_open"
```

`id` của cầu là **khóa của `Level.bridges`**, đồng thời là **chỉ số bit** trong `State.bridges`: cầu có `id = i` ứng với bit `1 << i`. Vì `id` liên tục từ 0 (luật 3) và tối đa 62 cầu (luật 7), mọi `id` đều hợp lệ làm chỉ số bit.

#### Tác động của công tắc lên cầu

```python
@dataclass(frozen=True, slots=True)
class Effect:
    mode: EffectMode
    bridges: tuple[int, ...]   # các id cầu được liên kết, không rỗng, không trùng
    mask: int                  # bitmask của các cầu đó, loader tính sẵn

    @staticmethod
    def create(mode: EffectMode, bridge_ids: Iterable[int]) -> "Effect":
        ids = tuple(sorted(set(bridge_ids)))
        mask = 0
        for i in ids:
            mask |= 1 << i
        return Effect(mode, ids, mask)
```

`mask` được tính một lần lúc nạp để `engine.step` chạy nhanh (solver gọi hàm này hàng triệu lần). Chỉ tạo `Effect` qua `Effect.create(...)`, không gọi trực tiếp constructor, để `bridges` và `mask` luôn khớp nhau.

#### Công tắc

```python
@dataclass(frozen=True, slots=True)
class Switch:
    pos: Pos
    type: SwitchType
    effect: Effect | None = None                    # bắt buộc với SOFT, HEAVY; phải là None với SPLIT
    split_targets: tuple[Pos, Pos] | None = None    # bắt buộc với SPLIT; phải là None với SOFT, HEAVY
```

Bất biến do loader đảm bảo (luật 9 ở 7.3):

| `type` | `effect` | `split_targets` |
|---|---|---|
| `SOFT` | có | `None` |
| `HEAVY` | có | `None` |
| `SPLIT` | `None` | có (2 ô, thứ tự `(a, b)` chính là khối lập phương số 0 và số 1) |

#### Level

```python
@dataclass(frozen=True)
class Level:
    name: str
    rows: int
    cols: int
    terrain: tuple[str, ...]          # grid đã chuẩn hóa
    start: Pos
    goal: Pos
    bridges: dict[int, Bridge]        # id -> Bridge
    bridge_at: dict[Pos, int]         # pos -> id
    switches: dict[Pos, Switch]       # pos -> Switch
```

Bảng ánh xạ từ JSON sang kiểu dữ liệu:

| JSON | Kiểu dữ liệu |
|---|---|
| `bridges[i].id` | khóa của `Level.bridges` và `Level.bridge_at` (giá trị) |
| `bridges[i].pos` | `Bridge.pos` và khóa của `Level.bridge_at` |
| `bridges[i].initial_open` | `Bridge.initial_open` |
| `switches[j].pos` | `Switch.pos` và khóa của `Level.switches` |
| `switches[j].type` | `Switch.type` (`SwitchType`) |
| `switches[j].effect.mode` | `Effect.mode` (`EffectMode`) |
| `switches[j].effect.bridges` | `Effect.bridges` và `Effect.mask` |
| `switches[j].split_targets` | `Switch.split_targets` |

#### Hàm áp dụng tác động (`mechanics/bridge.py`, do C viết)

Đây là hàm **duy nhất** được thay đổi bitmask cầu, để mọi nơi dùng chung một định nghĩa.

```python
def initial_bridges(level: Level) -> int:
    """Bitmask ban đầu: bit id = 1 nếu cầu đó có initial_open = True."""
    mask = 0
    for i, b in level.bridges.items():
        if b.initial_open:
            mask |= 1 << i
    return mask

def apply_effect(bridges: int, effect: Effect) -> int:
    """Trả bitmask cầu mới sau khi kích hoạt một công tắc."""
    if effect.mode is EffectMode.TOGGLE:
        return bridges ^ effect.mask
    if effect.mode is EffectMode.SET_OPEN:
        return bridges | effect.mask
    return bridges & ~effect.mask          # SET_CLOSE
```

Nếu một nước đi kích hoạt nhiều công tắc cùng lúc (khối nằm đáp trúng hai ô công tắc), `apply_effect` được gọi lần lượt theo thứ tự `cells(pose)` đã sắp xếp tăng dần theo `(r, c)`, để kết quả tái lập được.

Các test bắt buộc cho hàm này (`tests/test_mechanics.py`):

- `TOGGLE` hai lần liên tiếp trả về giá trị ban đầu.
- `SET_OPEN` và `SET_CLOSE` kích hoạt lần hai không làm thay đổi bitmask.
- Không bit nào ngoài `effect.mask` bị đổi.
- `initial_bridges` khớp với `initial_open` của từng cầu.

---

<!-- ## 8. Phân công module và người chịu trách nhiệm

| Module | Người chính | Người review chéo |
|---|---|---|
| `core/` (state, board, move, constants), `json_loader`, `tests/test_moves.py`, `test_levels.py` | **B** | C |
| `mechanics/` (fragile, bridge, switch, split), `core/engine.py` (phần điều phối), `tests/test_mechanics.py` | **C** | B |
| `solvers/bfs.py`, `dfs.py`, `ucs.py`, `base_solver.py`, `result.py`, `experiments/benchmark.py`, `tests/test_solvers.py` | **D** | A |
| `solvers/astar.py`, `heuristics.py`, `costs.py` (cùng D), `main.py`, README, requirements | **A** | D |
| `gui/`, `experiments/plot_results.py`, video | **E** | A |

--- -->

## 8. Định nghĩa hoàn thành (Definition of Done)

Một tính năng chỉ coi là xong khi:

- [ ] Có unit test và test pass.
- [ ] Đã qua review chéo và được merge bằng Pull Request.
- [ ] Không phá vỡ interface ở tài liệu này (nếu cần đổi, cập nhật tài liệu cùng PR).
- [ ] Với solver: lời giải **phát lại được trên engine** và dẫn đến goal; BFS và UCS (cost đều) cho cùng `solution_length`; A\* không cho chi phí lớn hơn UCS trên cùng màn.

---

## 9. Các quyết định cần cả nhóm xác nhận

| # | Vấn đề | Mặc định đề xuất |
|---|---|---|
| 1 | Khối lập phương có làm vỡ ô dễ vỡ không | Không |
| 2 | Hai khối lập phương có thể chồng lên nhau không | Không (`BLOCKED`) |
| 3 | Việc ghép khối có tự động không | Có, ngay khi kề cạnh |
| 4 | Công tắc `split` có tác động lên cầu không | Không, chỉ tách khối |
| 5 | Chuẩn hóa `(a, b)` ở `SplitPose` | Không |
| 6 | Thuật toán DFS hay IDS | Quyết định bởi D, ghi rõ trong báo cáo |
| 7 | Hàm chi phí của UCS | Theo gợi ý ở 6.5, chốt cùng A |
| 8 | Cầu đóng dưới chân khối thì khối rơi | Có (bước 4 ở mục 4.6) |

---

## 10. Quy ước làm việc

- Mỗi người một nhánh `feature/<tên>`, merge vào `dev` qua Pull Request, A duyệt.
- PR từ `feature/*` vào dev; sau khi sản phẩm hoàn tất, Team Lead tạo PR từ `dev` vào `main`.
- Không commit `__pycache__/`, kết quả tạm.
- Chạy từ thư mục gốc: `python main.py`. Import dùng đường dẫn tuyệt đối từ gốc, ví dụ `from src.core.state import State`.
- Mọi thay đổi interface (`State`, `Action`, `Engine`, `SolverResult`, schema JSON) phải cập nhật **tài liệu này trong cùng PR**.
- Môi trường: Python >= 3.10. Tất cả thành viên sử dụng Python 3.10+ và cài dependencies từ requirements.txt. Ghi phiên bản Python trong README.

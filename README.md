# Bloxorz AI Solver

Đồ án 1 môn **CSC14003: Nhập môn Trí tuệ nhân tạo**, Khoa Công nghệ Thông tin, Trường Đại học Khoa học Tự nhiên, ĐHQG-HCM.

Dự án cài đặt lại trò chơi **Bloxorz** (có giao diện đồ họa) và bốn bộ giải tự động: **BFS**, **DFS/IDS**, **UCS** và **A\***. Các thuật toán tìm kiếm đều được tự cài đặt, thư viện ngoài chỉ dùng cho giao diện, cấu trúc dữ liệu, đo lường và vẽ biểu đồ.

> **Video demo:** `<điền link YouTube công khai>`
> **Báo cáo:** `Report.pdf`

---

## Mục lục

1. [Tính năng](#1-tính-năng)
2. [Yêu cầu hệ thống](#2-yêu-cầu-hệ-thống)
3. [Cài đặt](#3-cài-đặt)
4. [Chạy chương trình](#4-chạy-chương-trình)
5. [Cấu trúc thư mục](#5-cấu-trúc-thư-mục)
6. [Kiến trúc tóm tắt](#6-kiến-trúc-tóm-tắt)
7. [Định dạng màn chơi](#7-định-dạng-màn-chơi)
8. [Chạy kiểm thử và thực nghiệm](#8-chạy-kiểm-thử-và-thực-nghiệm)
9. [Quy ước làm việc nhóm](#9-quy-ước-làm-việc-nhóm)
10. [Thành viên](#10-thành-viên)
11. [Tài liệu tham khảo](#11-tài-liệu-tham-khảo)

---

## 1. Tính năng

**Trò chơi**

- Khối 1×1×2 với ba tư thế (đứng, nằm ngang, nằm dọc) và bốn hướng lăn.
- Phát hiện nước đi sai (rơi khỏi bàn, rơi xuống ô trống) và phát hiện thắng (khối đứng trên ô đích).
- Ô nâng cao: ô dễ vỡ, cầu, công tắc mềm (soft), công tắc nặng (heavy), công tắc tách (split) với cơ chế tách và ghép khối; tác động lên cầu gồm `toggle`, `set_open` và `set_close`.
- Màn chơi nạp từ file JSON, dùng chung cho game và mọi solver.

**Bộ giải**

| Thuật toán | Ghi chú |
|---|---|
| BFS | Tối ưu về số nước đi khi chi phí đều |
| DFS / IDS | Có xử lý trạng thái lặp |
| UCS | Hàm chi phí không đồng nhất, định nghĩa trong `src/solvers/costs.py` |
| A\* | Heuristic admissible theo đúng hàm chi phí, định nghĩa trong `src/solvers/heuristics.py` |

Mỗi lần giải đều ghi lại: **thời gian tìm kiếm**, **bộ nhớ đỉnh**, **số node mở rộng**, **độ dài lời giải**.

**Giao diện (pygame-ce)**

- Chọn màn, New Game, Restart.
- Chơi bằng tay, hiển thị rơi, vỡ ô, thắng.
- Các nút Solve BFS / DFS / UCS / A\*, phát lại lời giải theo từng bước và bảng thống kê.

---

## 2. Yêu cầu hệ thống

- **Python 3.10 trở lên** (mã nguồn dùng `dataclass(slots=True)` và kiểu `X | Y`).
- Hệ điều hành: Windows, macOS hoặc Linux có hỗ trợ giao diện đồ họa.

---

## 3. Cài đặt

```bash
# 1. Lấy mã nguồn
git clone <url-repo>
cd Bloxorz-AI-Solver

# 2. (Khuyến nghị) tạo môi trường ảo
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

# 3. Cài thư viện
pip install -r requirements.txt
```

**Lưu ý:** dự án dùng **`pygame-ce`**, không phải `pygame`. Hai gói này xung đột nhau, nên **không cài cả hai** trong cùng một môi trường. Nếu đã cài `pygame`, hãy gỡ trước:

```bash
pip uninstall pygame
pip install pygame-ce
```

Thư viện chính (xem phiên bản chính xác trong `requirements.txt`):

| Thư viện | Mục đích |
|---|---|
| `pygame-ce` | Giao diện đồ họa |
| `matplotlib`, `pandas` | Vẽ biểu đồ và xử lý bảng kết quả thực nghiệm |
| `pytest` | Chạy kiểm thử |

---

## 4. Chạy chương trình

**Luôn chạy từ thư mục gốc của repo** để các import dạng `from src.core.state import State` hoạt động.

```bash
python main.py
```

Điều khiển cơ bản (cập nhật theo giao diện thực tế):

| Phím / thao tác | Chức năng |
|---|---|
| Phím mũi tên | Lăn khối theo 4 hướng |
| `Space` | Đổi khối đang điều khiển khi đã tách thành hai khối |
| Nút **Restart** | Chơi lại màn hiện tại |
| Nút **New Game** | Chọn màn khác |
| Nút **BFS / DFS / UCS / A\*** | Chạy bộ giải tương ứng, sau đó phát lại lời giải |

---

## 5. Cấu trúc thư mục

```
Bloxorz-AI-Solver/
├── README.md                    # Tài liệu này
├── requirements.txt             # pygame-ce, matplotlib, pandas, pytest, ...
├── .gitignore                   # __pycache__/, *.pyc, experiments/results/tmp/
├── main.py                      # Điểm vào: khởi chạy GUI
│
├── assets/                      # Tài nguyên cho GUI
│   ├── images/
│   ├── tiles/                   # Sprite các loại ô (floor, fragile, goal, bridge, switch...)
│   ├── buttons/
│   └── sounds/
│
├── levels/                      # Mỗi màn một file JSON
│   ├── README.md                # Mô tả schema JSON (bridge, switch, split, liên kết switch-bridge)
│   ├── level01.json
│   ├── level02.json
│   └── ...
│
├── src/
│   ├── __init__.py
│   │
│   ├── core/                    # Lõi: dữ liệu và luật cơ bản
│   │   ├── __init__.py
│   │   ├── constants.py         # Hướng đi, loại ô, tư thế khối
│   │   ├── state.py             # State bất biến + hashable (vị trí, tư thế, bridge, split)
│   │   ├── board.py             # Bản đồ, ô, ô đích, Level, Bridge, Switch, Effect
│   │   ├── move.py              # Bảng chuyển tư thế (orientation, direction) -> (orientation, pos)
│   │   ├── engine.py            # step(state, action), get_successors(), is_goal(), điều phối mechanics
│   │   └── utils.py
│   │
│   ├── mechanics/               # Cơ chế nâng cao (do engine.py gọi theo thứ tự cố định)
│   │   ├── __init__.py
│   │   ├── fragile.py           # Ô dễ vỡ
│   │   ├── bridge.py            # Cầu đóng/mở, apply_effect, initial_bridges
│   │   ├── switch.py            # Soft / Heavy / Split switch, toggle / permanent
│   │   └── split.py             # Tách và ghép khối (gồm merge)
│   │
│   ├── solvers/                 # Thuật toán tìm kiếm
│   │   ├── __init__.py
│   │   ├── result.py            # SolverResult: path, states, time, peak_memory, expanded_nodes, status...
│   │   ├── base_solver.py       # Interface chung + Stats + đo thời gian/bộ nhớ
│   │   ├── costs.py             # Hàm chi phí dùng chung cho UCS và A*
│   │   ├── heuristics.py        # Heuristic của A* (admissible theo costs.py)
│   │   ├── bfs.py
│   │   ├── dfs.py               # DFS hoặc IDS
│   │   ├── ucs.py
│   │   └── astar.py
│   │
│   ├── gui/                     # Giao diện Pygame
│   │   ├── __init__.py
│   │   ├── game.py              # Vòng lặp chính
│   │   ├── renderer.py          # Vẽ bàn cờ, ô, khối
│   │   ├── ui.py                # Nút, bảng thống kê
│   │   ├── controls.py          # Xử lý phím và chuột
│   │   └── animation.py         # Animation, replay lời giải
│   │
│   └── utils/                   # Tiện ích dùng chung
│       ├── __init__.py
│       ├── json_loader.py       # Đọc/kiểm tra file màn chơi
│       ├── logger.py
│       └── timer.py
│
├── tests/                       # Unit test
│   ├── __init__.py
│   ├── test_moves.py            # Bảng chuyển tư thế, nước đi hợp lệ
│   ├── test_mechanics.py        # Fragile, bridge, switch, split/merge
│   ├── test_solvers.py          # Lời giải hợp lệ khi phát lại trên engine; BFS = UCS (cost đều)
│   └── test_levels.py           # Mọi màn nạp được và có lời giải
│
├── experiments/                 # Thực nghiệm
│   ├── __init__.py
│   ├── benchmark.py             # Đo thời gian, bộ nhớ đỉnh, số node, độ dài lời giải
│   ├── run_all_levels.py        # Chạy toàn bộ solver trên bộ test cố định
│   ├── plot_results.py          # Vẽ biểu đồ từ CSV/JSON
│   └── results/                 # Xuất CSV/JSON
│
├── feedbacks/ 
│
└── docs/
    ├── architecture.md          # State, engine.step, SolverResult, thứ tự xử lý mechanics
    └── report_template.md
```

---

## 6. Kiến trúc tóm tắt

```
Level JSON ──► json_loader ──► Level ──► Engine ◄── Solvers (BFS / DFS / UCS / A*)
                                           ▲
                                           └────── GUI (chơi tay, replay lời giải)
```

Nguyên tắc chính:

- **Tách lớp:** `core` và `mechanics` (luật chơi) không biết gì về `gui` và `solvers`. Solver chỉ gọi engine qua `get_successors()` và `is_goal()`, nên chạy được không cần pygame.
- **`State` bất biến và hashable:** gồm tư thế khối (hoặc hai khối lập phương khi tách) và bitmask trạng thái các cầu, dùng trực tiếp làm khóa trong `set`/`dict`.
- **Một nguồn sự thật:** luật nước đi chỉ nằm trong `engine.py` (và `mechanics/*` do engine gọi).
- **Một nguồn chi phí:** `costs.py` dùng chung cho UCS và A\*, heuristic phải admissible theo đúng hàm chi phí đó.

Đặc tả đầy đủ (bảng chuyển tư thế, thứ tự xử lý `engine.step`, interface của Engine và Solver, các định nghĩa dùng cho thực nghiệm) nằm trong [`docs/architecture.md`](docs/architecture.md).

---

## 7. Định dạng màn chơi

Mỗi màn là một file JSON trong thư mục `levels/`. Ký tự trong `grid`:

| Ký tự | Ý nghĩa |
|---|---|
| `.` | Ô trống (không có sàn) |
| `#` | Sàn thường (ô công tắc cũng là `#`) |
| `S` | Ô bắt đầu, khối đứng ở đây |
| `G` | Ô đích |
| `F` | Ô dễ vỡ |

Cầu và công tắc khai báo trong danh sách riêng. Ví dụ:

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

Loại công tắc: `soft`, `heavy`, `split`. Chế độ tác động lên cầu: `toggle`, `set_open`, `set_close`. Công tắc `split` dùng `split_targets` thay cho `effect`. Schema chi tiết và các điều kiện kiểm tra khi nạp xem tại mục 7 của `docs/architecture.md`.

Hai level kiểm thử cơ chế nâng cao là `levels/level12.json` (soft/heavy và nhiều cầu) và `levels/level13.json` (tách/di chuyển/ghép khối).

---

## 8. Chạy kiểm thử và thực nghiệm

Chạy từ thư mục gốc của repo.

**Kiểm thử**

```bash
pytest                      # chạy toàn bộ
pytest tests/test_moves.py  # chỉ bảng chuyển tư thế
```

**Thực nghiệm (không mở giao diện)**

```bash
python -m experiments.run_all_levels   # chạy mọi solver trên bộ test cố định, ghi kết quả vào experiments/results/
python -m experiments.plot_results     # vẽ biểu đồ từ kết quả
```

Cách đo, theo định nghĩa thống nhất cho cả bốn thuật toán:

- **Thời gian:** `time.perf_counter()`, chạy nhiều lần và lấy trung vị.
- **Bộ nhớ:** peak của `tracemalloc` (chỉ tính bộ nhớ Python theo dõi được, không phải toàn bộ RAM tiến trình), đo ở lượt chạy riêng vì `tracemalloc` làm chậm chương trình.
- **Node mở rộng:** số lần một node được lấy khỏi frontier và được sinh nước đi kế tiếp.
- **Độ dài lời giải:** số nước đi trong `path`.

---

## 9. Quy ước làm việc nhóm

- Mỗi người làm trên nhánh `feature/<tên>`, tạo Pull Request vào `dev`, Team Lead duyệt.
- Khi sản phẩm hoàn tất, Team Lead tạo Pull Request từ `dev` vào `main`.
- Không commit `__pycache__/` và các kết quả tạm.
- Mọi thay đổi interface (`State`, `Action`, `Engine`, `SolverResult`, schema JSON) phải cập nhật `docs/architecture.md` trong cùng Pull Request.
- Một tính năng chỉ coi là xong khi có unit test pass và đã qua review chéo.

---

## 10. Thành viên

| Vai trò | Họ tên | MSSV | Phụ trách chính |
|---|---|---|---|
| A (Team Lead) | Minh Quang | 24120420 | Kiến trúc, A\*, heuristic, tích hợp, biên tập báo cáo |
| B | Mai Đăng Khoa | 24120346 | Engine cơ bản, loader, test màn chơi |
| C | Lâm Anh Khang | 24120335 | Cơ chế nâng cao (cầu, công tắc, tách/ghép) |
| D | Nguyễn Trọng Phú | 24120410 | BFS, DFS/IDS, UCS, benchmark |
| E | Trần Thanh Tùng | 20120409 | Giao diện, biểu đồ thực nghiệm, video |

Tỷ lệ đóng góp của từng thành viên được ghi trong `Report.pdf`.

---

## 11. Tài liệu tham khảo

- S. Russell, P. Norvig, *Artificial Intelligence: A Modern Approach* (các chương về tìm kiếm không có thông tin và có thông tin).
- Bloxorz, Coolmath Games: https://www.coolmathgames.com/0-bloxorz
- Tài liệu `pygame-ce`: https://pyga.me/docs/
- Danh sách đầy đủ, kèm phần mô tả cách sử dụng công cụ AI, xem ở mục Tài liệu tham khảo và Phụ lục của `Report.pdf`.

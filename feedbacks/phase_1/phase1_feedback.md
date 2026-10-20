# Feedback Giai đoạn 1: Bloxorz AI Solver

> **Ngày tổng kết:** 17/10/2026
> **Phạm vi:** `architecture_v2.md`, `base_solver.py`, `bfs.py`, `result.py`, `test_solvers.py`, và các file test `test_moves.py`, `test_levels.py`, `test_mechanics.py`.
> **Cách kiểm tra:** với phần solver, các file được chép vào một bản sao tạm và chạy `pytest` thật (kể cả với `PYTHONTRACEMALLOC=1` để giả lập `tracemalloc` bật từ ngoài). Với các file test của engine, chưa có mã nguồn engine nên giá trị kỳ vọng được đối chiếu thủ công với `architecture_v2.md`.

---

## 1. Kết luận nhanh

| Hạng mục | Kết quả |
|---|---|
| `base_solver.py`, `bfs.py`, `result.py` | **Đạt.** 15/15 test pass, các lỗi nghiêm trọng đã sửa |
| `test_solvers.py` | **Đạt** |
| `test_moves.py`, `test_levels.py`, `test_mechanics.py` | Giá trị kỳ vọng đều đúng, độ phủ chưa đủ cho giai đoạn 1 |
| Test "đóng cầu thì rơi" | đã thêm và pass |


---

## 2. Đã sửa gì và vì sao

### 2.1. Solver: `base_solver.py`, `bfs.py`, `result.py`

| # | Đã sửa | Trước đó có vấn đề gì | Vì sao quan trọng |
|---|---|---|---|
| 1 | `path` giữ nguyên kiểu `Action`, bỏ `action_to_str` | Đường đi bị đổi thành chuỗi | Engine thật trả `Action`, nên chuỗi không phát lại được trên `step`. GUI replay và kiểm tra "lời giải phát lại đúng" ở Definition of Done đều cần `Action` thật |
| 2 | Thêm cờ `measure_memory`, bật/tắt `tracemalloc` trong `solve()` | `tracemalloc` bật trước khi bấm giờ, nên thời gian đo luôn bị làm chậm | Đặc tả yêu cầu hai lượt đo riêng (thời gian, bộ nhớ). Thuật toán cấp phát nhiều (BFS, UCS) sẽ bị phạt nặng hơn nếu không tách |
| 3 | `tracemalloc.stop()` đặt trong `finally`, chỉ tắt khi chính `solve()` bật | Lần đầu thì không tắt, lần sau thì tắt cả thứ mình không bật | Nếu không tắt, các lượt đo thời gian sau đó vẫn bị chậm vĩnh viễn trong tiến trình |
| 4 | Tách `started_here` khỏi `measure_memory` | Khi `tracemalloc` đã chạy sẵn, `peak_memory` âm thầm bằng 0 | Số liệu sai mà không báo lỗi, khó phát hiện nhất |
| 5 | `search_time` tính trong `finally`, trước khi đọc bộ nhớ và `stop()` | Cộng cả thời gian của các lệnh `tracemalloc` | Giữ thời gian chỉ gồm phần tìm kiếm |
| 6 | Goal test khi **lấy node ra khỏi frontier**, không phải lúc sinh node | `diamond_graph` đếm 3 node mở rộng, đúng ra là 4 | Mục 6.3 yêu cầu cùng một luật cho cả 4 thuật toán. UCS và A\* bắt buộc làm vậy để tối ưu. Nếu BFS khác, BFS trông rẻ hơn chỉ vì luật đếm |
| 7 | `STATUS_LIMIT` tách thành `STATUS_TIMEOUT` và `STATUS_NODE_LIMIT`, `SearchLimitReached` mang `status` | Một trạng thái chung cho hai nguyên nhân | Bảng thực nghiệm cần phân biệt "hết giờ" với "quá số node" |
| 8 | `max_expanded` → `node_limit`, `limit_exceeded` → `check_limits`, `>` → `>=` | Tên cũ nghe như trả `bool` nhưng thực ra ném ngoại lệ; `time_limit=0.0` chập chờn trên đồng hồ thô | Cùng tên với đặc tả; `time_limit=0` luôn dừng ngay |
| 9 | `check_limits` đặt **sau** goal test, ngay trước `on_expand()` | Đặt ở đầu vòng lặp nên `node_limit=4` trên đồ thị cần đúng 4 lần mở rộng vẫn báo `node_limit` | Giới hạn N nghĩa là "được mở rộng tối đa N node". Việc lấy node goal ra không được bị chặn. DFS, UCS, A\* sẽ copy cách đặt này |
| 10 | `SolverResult` thêm `algorithm`, `solution_length`, `total_cost`, `generated_nodes`, `max_frontier`; `time` → `search_time`; `peak_memory` là `int` byte | Thiếu các trường mà benchmark và báo cáo cần; MB dạng `float` dễ sai số | Thống nhất đơn vị (byte), đổi sang MB khi vẽ biểu đồ |
| 11 | `total_cost = inf` khi không có lời giải | Có thời điểm bằng `0.0` | Thuật toán thất bại không được trông như "rẻ nhất" khi lấy trung bình hay xếp hạng |
| 12 | Xóa `limit_exceeded` cũ và code cũ bị comment ở `result.py`, `bfs.py` | Hai hàm gần giống nhau cùng tồn tại (một dùng `>`, một dùng `>=`) | Người viết DFS, UCS sau này có thể gọi nhầm hàm cũ |

**Kiểm chứng thực tế (17/10):**

- `node_limit`: 3 → `node_limit`, 4 → `solved`, 5 → `solved`. Đúng ranh giới.
- `limit_exceeded` đã biến mất khỏi mã.
- 15/15 test pass khi chạy bình thường.

### 2.2. Test của solver: `test_solvers.py`

| Test | Bắt lỗi gì |
|---|---|
| `expanded_nodes == 4`, `generated_nodes == 5`, `max_frontier == 2` | Luật đếm node theo mục 6.3. Đã đếm tay: A, B, C, D mở rộng rồi lấy G ra |
| `peak_memory > 0` (thay cho `>= 0`) | `>= 0` luôn đúng, kể cả khi code không đo gì |
| `test_bfs_timeout` (`time_limit=0.0`) | Cơ chế `deadline` và `check_limits` |
| `test_bfs_node_limit_exactly_enough` | Lỗi lệch một node ở mục 9 phía trên |
| `test_tracemalloc_is_stopped_after_solve`, `..._even_when_limit_hit` | Rò `tracemalloc` (nhánh `finally`) |
| `test_peak_memory_when_tracemalloc_already_running` | Lỗi `peak_memory = 0` khi `tracemalloc` bật sẵn |
| `test_bfs_measure_memory_off_does_not_start_tracemalloc` | Lượt đo thời gian không bị `tracemalloc` làm chậm |
| `test_unsolved_total_cost_is_inf` | `total_cost = 0.0` khi thất bại |
| `result.algorithm == "bfs"`, các bất biến `solution_length`, `len(states) == len(path) + 1` | Bất biến của `SolverResult` ở mục 6.1 |
| `@pytest.mark.skipif(tracemalloc.is_tracing(), ...)` | Tránh "fail oan" khi chạy với `tracemalloc` bật từ ngoài |

### 2.3. Đặc tả: `architecture.md` v1 → v2

| Đã sửa | Vì sao |
|---|---|
| Thêm định nghĩa `Bridge`, `Switch`, `Effect`, `apply_effect`, `initial_bridges` (mục 7.4) | B (loader) và C (cơ chế) không phải tự đoán kiểu dữ liệu, tránh lệch nhau |
| Thêm `INVALID_ACTION` và bước 0 trong `step` | Hành động sai chế độ (ví dụ `cube=0` khi khối còn nguyên) phải có kết quả xác định |
| Bỏ `found`, thay bằng `status` với 4 giá trị | Phân biệt vô nghiệm, hết giờ, quá node |
| Thêm `Stats`, `SearchLimitReached`, hợp đồng `_search` (trả `(actions, states)` hoặc `None`) | Cả nhóm viết solver theo cùng một khung. Mục 6.1 và 6.2 hiện khớp code của D |
| Quy ước heap `(priority, counter, node)` | `State` không so sánh được, nếu không sẽ `TypeError` khi hòa điểm. Counter cũng giúp kết quả tái lập |
| Ghi chú `tracemalloc` là "peak Python-tracked memory" | Trung thực về phạm vi của số đo, báo cáo sẽ cần |
| Thêm luật loader 8 đến 12 | Bắt dữ liệu màn chơi sai sớm, với thông báo rõ ràng |
| Ràng buộc Python ≥ 3.10, quy ước nhánh `dev` → `main` | `slots=True` và kiểu `X \| Y` cần 3.10; làm rõ luồng merge |
| Đầu tài liệu dùng tên thật (Minh Quang) | Người duyệt thay đổi phải xác định được |

---


**Chi tiết việc 8 (độ phủ test engine):**

- **`test_moves.py`:** 12 trường hợp bảng chuyển đều đúng. Thiếu test `cells()`, test lăn rồi lăn ngược trở về pose cũ (mình đã chạy thử, đúng với cả 12 trường hợp), và test engine cơ bản (thứ tự `get_successors`, rơi ra ngoài, `is_goal`).
- **`test_levels.py`:** mới phủ 2 trong 12 luật loader. `test_load_invalid_start` có hai lỗi cùng lúc (hai `S` và không có `G`), nên chỉ pass nếu loader kiểm tra `S` trước `G`. Thiếu test nạp mọi file trong `levels/`.
- **`test_mechanics.py`:** 19 test, giá trị đều khớp đặc tả. Cần sửa hàng 2 của một level (`"####"` chỉ 4 ký tự trong khi `cols = 5`), vài ô cầu đặt trên ô không phải `.`, đổi tên test số 19. Thiếu test cầu đóng/mở cho khối đi qua (test này theo báo cáo đã thêm), `is_goal`, ghép khối dọc, khối lập phương không kích hoạt công tắc heavy và split. Hai test `ValueError` (`Effect.create`, `apply_effect` với mode lạ) yêu cầu hành vi chưa có trong đoạn code mẫu của mục 7.4, cần bổ sung vào đặc tả.
- **`BLOCKED`** không thể xảy ra ở trạng thái đạt tới được (đã mô phỏng 20.000 lượt, 0 lần). Hai khối kề cạnh thì tự ghép, và `split_targets` không kề nhau, nên khối này không thể bước lên ô của khối kia. Có thể giữ làm kiểm tra phòng thủ, nhưng quyết định số 2 ở mục 9 thực chất không còn ý nghĩa.

---


## 3. Bài học rút ra

1. **Sửa đặc tả và code trong cùng một Pull Request.** Dòng 315 lệch với code chính vì hai việc này được làm ở hai thời điểm khác nhau.
2. **Tính tay số kỳ vọng trước khi viết test** (như `expanded_nodes == 4`), rồi để test xác nhận, không viết test cho khớp với đầu ra của code.
3. **Mỗi test chỉ có một lỗi.** Một lưới vừa có hai `S` vừa thiếu `G` làm test phụ thuộc vào thứ tự kiểm tra của loader.
4. **Bắt tên hàm test trùng tự động.** Pytest không cảnh báo khi hai hàm trùng tên, hàm sau đè hàm trước. Chạy linter như `ruff` hoặc `flake8` (quy tắc `F811`, "redefinition of unused name") trước mỗi lần tạo Pull Request.
5. **Ưu tiên lỗi âm thầm.** Hai lỗi nguy hiểm nhất giai đoạn này đều không báo lỗi gì: `peak_memory = 0` khi `tracemalloc` bật sẵn, và `total_cost = 0.0` khi thất bại. Với phần đo lường, đáng bỏ thêm thời gian viết test cho chúng.

# Hàm chi phí và heuristic của A\*: thiết kế và chứng minh

> Tài liệu này đi kèm `src/solvers/costs.py` và `src/solvers/heuristics.py`, dùng làm nền cho mục "Heuristic" trong báo cáo.

---

## 1. Hàm chi phí (`costs.py`)

Chi phí của một nước đi `s --a--> s'`:

```
c(s, a, s') = 1 + 1·[ s'.pose là khối nguyên và có ô nằm trên ô dễ vỡ ]
```

| Thành phần | Giá trị | Lý do |
|---|---|---|
| Chi phí cơ bản | 1 | Công sức của một lần lăn |
| Phạt ô dễ vỡ | +1 | Ô dễ vỡ chỉ an toàn khi khối nằm. Một nước đi sai là khối đứng lên đó và rơi, nên đường đi qua ô dễ vỡ là đường rủi ro và bị tính đắt gấp đôi |
| Khối lập phương (sau khi tách) | không phạt | Theo quy ước nhóm, khối lập phương không làm vỡ ô dễ vỡ nên không có rủi ro |
| Nước đi kích hoạt công tắc | không giảm giá | Chi phí < 1 sẽ làm `C_MIN` nhỏ xuống và heuristic yếu đi tương ứng (xem mục 5) |

Hệ quả: UCS khác BFS (chi phí không đồng nhất), và UCS tìm đường **ít rủi ro nhất** thay vì chỉ ít nước nhất.

Hai tính chất mà phần chứng minh dựa vào:

- **(C1)** `c ≥ C_MIN = 1 > 0` với mọi nước đi.
- **(C2)** `c` chỉ phụ thuộc vào **tư thế mới** `s'.pose` và địa hình tĩnh, không phụ thuộc trạng thái cầu, hành động hay trạng thái trước.

---

## 2. Heuristic (`heuristics.py`)

### 2.1. Bài toán nới lỏng R

R giữ nguyên các luật tĩnh và bỏ mọi thứ động:

- **Bỏ** cầu và công tắc: mọi ô cầu coi như sàn (vì cầu có thể đang mở).
- **Giữ** biên bàn, ô trống `.` vĩnh viễn, và luật "khối đứng không được ở trên ô dễ vỡ".
- Mỗi nước lăn có chi phí `roll_cost` đúng như ở `costs.py`.
- Không có tách khối.

Gọi `D_goal(p)` là chi phí ngắn nhất trong R từ tư thế `p` đến tư thế **đứng trên ô đích**, và `D_split(p)` là chi phí ngắn nhất trong R từ `p` đến việc **đứng trên một công tắc split**. Cả hai được tính trước bằng Dijkstra trên đồ thị ngược, một lần cho mỗi màn.

### 2.2. Định nghĩa

```
h(s) = min( D_goal(s.pose) ,  D_split(s.pose) + 2·C_MIN )     nếu s.pose là khối nguyên
h(s) = 2·C_MIN                                                  nếu s.pose là hai khối lập phương
```

Hằng `2·C_MIN` ở chế độ tách có nghĩa: từ trạng thái tách còn **ít nhất 2 nước đi**. Một nước để hai khối ghép lại (khối ghép luôn **nằm**, không phải trạng thái goal), một nước nữa để dựng lên đứng trên ô đích. Goal chỉ xảy ra khi khối nguyên đứng trên `G`.

---

## 3. Admissible: `h(s) ≤ h*(s)`

Với `h*(s)` là chi phí tối ưu thật từ `s` đến goal.

**Bổ đề 1.** Mọi nước đi thật giữa hai khối nguyên là một cạnh của R, với cùng chi phí.
*Chứng minh.* Nước đi thật hợp lệ nghĩa là mọi ô của tư thế mới được nâng đỡ xét cả cầu, ô trống, ô dễ vỡ. Điều kiện nâng đỡ tĩnh của R (cầu coi như sàn, giữ ô trống vĩnh viễn và luật ô dễ vỡ) chỉ lỏng hơn, nên tư thế đó cũng hợp lệ trong R. Bảng chuyển tư thế giống nhau. Chi phí bằng nhau theo (C2). ∎

**Định lý 1.** `h(s) ≤ h*(s)` với mọi `s`.

*Chứng minh.* Xét một đường đi tối ưu thật từ `s` đến goal (nếu không có thì `h* = ∞` và hiển nhiên đúng).

- **`s` đang ở chế độ tách.** Goal đòi hỏi khối nguyên, nên đường đi cần ít nhất một nước ghép, rồi khối ghép (đang nằm) cần thêm ít nhất một nước để đứng. Mỗi nước tốn ít nhất `C_MIN` theo (C1), nên `h*(s) ≥ 2·C_MIN = h(s)`.
- **`s` là khối nguyên, đường đi không bao giờ tách.** Mọi nước đi là nước giữa hai khối nguyên, nên theo Bổ đề 1 đường đi là một đường trong R. Chi phí của nó ≥ `D_goal(s)`.
- **`s` là khối nguyên, đường đi có tách.** Gọi `p` là công tắc split đầu tiên mà khối đứng lên. Đoạn đi **trước** lần tách đầu chỉ gồm nước đi giữa khối nguyên, nên là một đường trong R kết thúc ở tư thế đứng trên `p`: chi phí ≥ `D_split(s)`. Đoạn **sau** là xuất phát từ trạng thái tách, nên theo ý đầu có chi phí ≥ `2·C_MIN`. Tổng ≥ `D_split(s) + 2·C_MIN`.

Hai trường hợp cuối cho `h*(s) ≥ min(D_goal(s), D_split(s) + 2·C_MIN) = h(s)`. ∎

---

## 4. Consistent: `h(s) ≤ c(s, a, s') + h(s')`

**Định lý 2.** `h` consistent, và `h(goal) = 0`.

*Chứng minh.* Xét từng loại cạnh `s → s'`.

1. **Khối nguyên → khối nguyên (không tách).** Đây là cạnh của R (Bổ đề 1). Khoảng cách ngắn nhất thỏa bất đẳng thức tam giác: `D_goal(s) ≤ c + D_goal(s')` và `D_split(s) ≤ c + D_split(s')`. Lấy min của hai vế (cộng hằng `2·C_MIN` cho vế thứ hai) vẫn giữ bất đẳng thức, nên `h(s) ≤ c + h(s')`.
2. **Khối nguyên → trạng thái tách.** Nước đi này là nước lăn dừng ở tư thế **đứng trên công tắc split** `p`, nên `s → (đứng trên p)` là một cạnh của R với chi phí `c` (ô công tắc là sàn thường, không bị phạt, nên chi phí thật và chi phí trong R bằng nhau) và `D_split(s) ≤ c`. Do đó `h(s) ≤ D_split(s) + 2·C_MIN ≤ c + 2·C_MIN = c + h(s')`.
3. **Tách → tách.** `h(s) = 2·C_MIN ≤ c + 2·C_MIN = c + h(s')` vì `c ≥ 0`.
4. **Tách → khối nguyên (ghép).** Khối ghép luôn **nằm**, nên cần ≥ 1 nước để đứng trên ô đích và ≥ 1 nước để đứng trên công tắc split: `h(s') ≥ C_MIN`. Cùng với `c ≥ C_MIN` ta có `c + h(s') ≥ 2·C_MIN = h(s)`.
5. **Goal.** `D_goal` của tư thế đích bằng 0 nên `h(goal) = 0`. Mọi `h ≥ 0`. ∎

**Hệ quả.** Consistent và `h(goal) = 0` kéo theo admissible (một chứng minh thứ hai). A\* với tập đóng (closed set) không cần mở lại node, và lời giải đầu tiên lấy ra khỏi hàng đợi là tối ưu.

---

## 5. Giới hạn và vì sao chọn như vậy

- **Heuristic bỏ qua cầu và công tắc.** Nếu lời giải phải đi vòng qua công tắc để mở cầu, `h` sẽ thấp hơn chi phí thật. Đây là cái giá để giữ admissible và tính được trước.
- **Chế độ tách chỉ có cận dưới hằng số 2.** Giai đoạn tách thường ngắn nên ảnh hưởng nhỏ, nhưng đây là chỗ có thể cải thiện về sau (ví dụ tính khoảng cách các khối đến việc ghép lại).
- **Chi phí `C_MIN`.** Nếu đổi sang chi phí < 1 (ví dụ công tắc "rẻ" 0,5) thì `C_MIN = 0,5`, các hằng `2·C_MIN` và mọi khoảng cách nhỏ đi một nửa, heuristic vẫn đúng nhưng yếu đi nhiều.

**Khi nào phải chứng minh lại:** nếu đổi `step_cost` để phụ thuộc trạng thái cầu (vi phạm C2), thêm cơ chế dịch chuyển mới ngoài split, hoặc đổi luật để khối lập phương làm vỡ ô dễ vỡ hay công tắc split tác động lên cầu (chỉ cần rà lại Bổ đề 1).

---

## 6. Kiểm chứng bằng thực nghiệm

`tests/test_heuristics.py` vét cạn không gian trạng thái của từng màn nhỏ, tính `h*` bằng Dijkstra ngược và kiểm tra hai bất đẳng thức trên **mọi** trạng thái và **mọi** cạnh.

Trong lúc soạn, mình cũng chạy phép kiểm tra tương tự trên **800 màn ngẫu nhiên** (chạy trên một engine tham chiếu viết lại theo `architecture.md`, chưa phải engine của nhóm): trong đó khoảng 420 màn có lời giải, khoảng 280 màn có công tắc split, tổng cộng hơn 120.000 trạng thái và 570.000 cạnh. Kết quả: **0 vi phạm admissible, 0 vi phạm consistent**.

Để chắc rằng phép kiểm tra có tác dụng, mình cố ý làm hỏng heuristic theo ba cách (tăng hằng số chế độ tách lên 3, bỏ qua split, cộng thêm 0,5 vào cạnh của R) và cả ba lần phép kiểm tra đều phát hiện vi phạm.

Con số tham khảo cho phần thảo luận (từ engine tham chiếu, **chưa phải số liệu cho báo cáo**, hãy chạy lại trên engine thật):

| Màn mẫu | Chi phí tối ưu | UCS mở rộng | A\* mở rộng |
|---|---|---|---|
| plain | 5,0 | 17 | 5 |
| fragile | 9,0 | 16 | 6 |
| bridge | 8,0 | 28 | 8 |
| split + bridge + fragile | 8,0 | 51 | 7 |

A\* và UCS ra cùng chi phí tối ưu trên cả bốn màn, như lý thuyết đòi hỏi.

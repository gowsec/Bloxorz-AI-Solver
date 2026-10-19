# Bước 1: Khung Pygame-ce và level viết tay

Chạy tại thư mục gốc (Python 3.10+):

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

Nếu đã có `.venv` thì bỏ qua lệnh tạo môi trường. `pygame-ce` được import bằng
`import pygame`. Không cài đồng thời gói `pygame` trong cùng môi trường.

Sửa `src/gui/sample_level.py` để thay bàn cờ. Mỗi chuỗi là một hàng, mọi hàng
cùng độ dài: `.` trống, `#` sàn, `S` bắt đầu, `G` đích, `F` dễ vỡ.
Phải có đúng một S và một G. Tọa độ dùng `(hàng, cột)` từ 0.

`Level.from_grid` kiểm tra dữ liệu và chuyển S/G thành sàn trong `terrain`,
lưu tọa độ riêng. GUI vẽ bàn cờ nhìn từ trên xuống và ký hiệu khối đứng ở S.
ESC hoặc nút đóng cửa sổ để thoát. Cửa sổ co giãn, giới hạn 60 FPS.

Đây là bản xem bàn cờ: chưa có di chuyển, luật thắng/thua, cầu/công tắc,
đọc JSON hoặc solver. README gốc mô tả mục tiêu toàn dự án.

`core/board.py` hiện mới có các trường cơ bản của Level. Các trường cầu và công
tắc trong `architecture.md` sẽ được bổ sung khi triển khai loader/mechanics.
Factory `from_grid` là đường tạo level tạm cho mốc này, trước loader JSON.

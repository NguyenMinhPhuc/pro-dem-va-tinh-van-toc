# QUY TẮC PHÁT TRIỂN VÀ KỸ NĂNG BẮT BUỘC DÀNH CHO AI (AI DEVELOPMENT GUIDELINES)
> **Dự án:** AutoGuardian - Hệ thống Giám sát & Bãi đỗ xe Thông minh Real-time  
> **Áp dụng cho:** Tất cả các AI Agent/Copilot thực hiện viết code, refactor hoặc thiết kế hệ thống.

---

## I. TỔNG QUAN STACK CÔNG NGHỆ BẮT BUỘC (TECH STACK)

Khi sinh code hoặc kiến trúc cho dự án, AI **bắt buộc** tuân thủ đúng các công nghệ và thư viện sau:

* **Ngôn ngữ lập trình:** Python 3.10+
* **Thị giác máy tính & AI:**
  * `ultralytics` (YOLOv8 - ưu tiên `yolov8n.pt` hoặc `yolov8s.pt` cho real-time)
  * `opencv-python` (OpenCV 4.x - Xử lý khung hình, luồng video, vẽ overlay)
  * `lap` / `scikit-learn` / `filterpy` (Hỗ trợ ByteTrack / SORT)
  * `numpy` (Tính toán đại số tuyến tính & ma trận điểm ảnh)
* **Giao diện người dùng (GUI):** `PyQt5` hoặc `CustomTkinter`
* **Đa luồng (Concurrency):** Python `threading`, `multiprocessing`, hoặc `QThread` (PyQt5)
* **Lưu trữ & Báo cáo:**
  * `sqlite3` (Lưu log sự kiện cục bộ)
  * `pandas` & `openpyxl` (Xuất báo cáo Excel/CSV)

---

## II. QUY TẮC THIẾT KẾ KIẾN TRÚC & QUẢN LÝ DỰ ÁN

### 1. Kiến trúc Đa luồng (Multi-threading Architecture)
* **BẮT BUỘC:** Tách biệt hoàn toàn luồng **Giao diện (UI Thread)** và luồng **Xử lý AI/Video (Worker Thread)**. 
* **KHÔNG BAO GIỜ** chạy mô hình YOLO hoặc đọc `VideoCapture` trực tiếp trên Main Thread của GUI để tránh hiện tượng "Not Responding" / treo giao diện.
* **Tín hiệu (Signals/Queues):** Dùng `QThread` & `pyqtSignal` (trong PyQt5) hoặc `queue.Queue` để giao tiếp giữa luồng đọc camera, luồng AI và luồng giao diện.

### 2. Cấu trúc Thư mục Chuẩn (Project Structure)
AI phải tuân thủ và sắp xếp code theo cấu trúc sau:

```text
AutoGuardian/
├── assets/                  # Tài nguyên tĩnh (icons, styles, test videos)
├── configs/                 # File cấu hình (config.json, zones.json)
├── models/                  # Chứa file weights (.pt, .onnx)
├── outputs/                 # Lưu video ghi hình, báo cáo Excel, bằng chứng vi phạm
│   ├── captures/            # Ảnh chụp vi phạm (.jpg)
│   └── reports/             # Báo cáo (.xlsx, .csv)
├── src/                     # Mã nguồn chính
│   ├── core/                # AI Engine, Tracking, Line Crossing Analytics
│   ├── gui/                 # PyQt5 Main Window, Widgets, Canvas
│   ├── streaming/           # Video Reader, Queue Manager, RTSP Handler
│   ├── storage/             # Database SQLite, Exporter, Logger
│   └── utils/               # Math helper functions, Draw utilities
├── app.py                   # Entrypoint chính của ứng dụng
├── requirements.txt         # Các thư viện phụ thuộc
└── README.md
```

---

## III. QUY TẮC CLEAN CODE & HIỆU NĂNG REAL-TIME

### 1. Tối ưu hóa Tốc độ Real-time (Performance Optimization)
* **Kích thước đầu vào:** Luôn `resize` khung hình về chuẩn $640 \times 640$ (hoặc $416 \times 416$) trước khi đưa vào mô hình YOLOv8.
* **Quản lý Hàng đợi (Frame Dropping):** Nếu hàng đợi frame vượt quá 2-3 frames, AI phải chủ động bỏ qua (drop) các frame cũ để ưu tiên xử lý frame mới nhất, giữ latency ở mức nhỏ nhất.
* **Tránh Rò rỉ Bộ nhớ (Memory Leak):** Giải phóng bộ nhớ OpenCV `VideoCapture` và `VideoWriter` đúng cách bằng khối `try...finally` hoặc `with` statement. Tránh append liên tục frame thô vào list trong RAM.
* **Chỉ chạy Tracking khi có Bounding Box:** Bỏ qua bước tracking nếu frame không phát hiện bất kỳ object nào.

### 2. Nguyên tắc Viết Code (Coding Standards)
* **Type Hinting:** Tất cả các hàm/phương thức phải có Type Annotation rõ ràng.
  ```python
  def calculate_centroid(bbox: tuple[int, int, int, int]) -> tuple[int, int]:
      x1, y1, x2, y2 = bbox
      return int((x1 + x2) / 2), int((y1 + y2) / 2)
  ```
* **Docstrings:** Tất cả module, class và function phải kèm Google-style docstring tiếng Việt hoặc tiếng Anh.
* **Đặt tên biến & Hàm (Naming Conventions):**
  * Class: `PascalCase` (vd: `CarDetector`, `VideoThread`)
  * Biến & Hàm: `snake_case` (vd: `confidence_threshold`, `process_frame`)
  * Hằng số: `UPPER_SNAKE_CASE` (vd: `DEFAULT_CONF_THRESHOLD = 0.5`)
* **Xử lý Ngoại lệ (Exception Handling):**
  * Không sử dụng `except Exception: pass` trống rỗng.
  * Mọi ngoại lệ liên quan đến ngắt kết nối Camera RTSP hoặc lỗi đọc file video phải được bắt cụ thể (`cv2.error`, `ConnectionError`) và có cơ chế fallback.

---

## IV. QUY TẮC LOGIC NGHIỆP VỤ CỐT LÕI (CORE LOGIC RULES)

### 1. Logic Đếm xe qua vạch (Line Crossing Analytics)
* Tọa độ vạch ảo được biểu diễn bằng 2 điểm $P_1(x_1, y_1)$ và $P_2(x_2, y_2)$.
* AI phải dùng phép toán Tích hướng (Cross Product) hoặc thuật toán giao cắt đoạn thẳng để kiểm tra xem tọa độ tâm $C(x, y)$ của `Track ID` có vừa di chuyển qua đường thẳng $P_1P_2$ hay không.
* **QUAN TRỌNG:** Mỗi `Track ID` chỉ được phép kích hoạt tăng bộ đếm **đúng 1 lần duy nhất** trong suốt vòng đời của nó.

### 2. Logic Cảnh báo Đỗ xe Trái phép (Parking Violation)
* Kiểm tra tâm xe $C(x, y)$ nằm trong đa giác ROI bằng thuật toán `cv2.pointPolygonTest`.
* Nếu xe nằm trong ROI, duy trì đếm thời gian ($T_{stay}$). Nếu $T_{stay} > T_{threshold}$ (ví dụ 30 giây) và độ dịch chuyển $\Delta d < \epsilon$, kích hoạt sự kiện vi phạm và lưu bằng chứng.

### 3. Thay đổi và thêm mới
- Khi có bất kỳ thay đổi và thêm mới chức năng phải phân tích và hỏi để xác nhận.
- Khi muốn thay đổi công nghệ phải đưa ra 2 giải giải pháp để chọn
---

## V. CHECKLIST KIỂM THỬ TRƯỚC KHU XUẤT CODE (DEFINITION OF DONE)

Mọi đoạn mã AI tạo ra cho dự án AutoGuardian chỉ được xem là hoàn thành khi đáp ứng đủ các tiêu chuẩn sau:

- [ ] Code không chứa "Magic Numbers" (các hằng số phải được khai báo rõ ràng).
- [ ] Mọi thao tác I/O (File, Camera, Database) đều nằm trong khối `try...except`.
- [ ] Không có Warning nào từ Linter (`flake8` / `black` / `pylint`).
- [ ] Đã kiểm tra tính năng giải phóng RAM / GPU Memory sau khi dừng video.
- [ ] Đã tách biệt hoàn toàn Logic AI khỏi UI components.
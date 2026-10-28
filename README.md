# AutoGuardian - Hệ Thống Giám Sát & Bãi Đỗ Xe Thông Minh Real-time

> **Học phần:** Thị giác Máy tính (Computer Vision) & Phát triển Ứng dụng Python  
> **Phiên bản:** 1.0.0  
> **Ngôn ngữ:** Python 3.10+ / 3.11  

📥 [Tải bộ cài (Releases)](https://github.com/NguyenMinhPhuc/pro-dem-va-tinh-van-toc/releases/latest) ·
📖 [Hướng dẫn sử dụng](HUONG_DAN_SU_DUNG.md) ·
🔏 [Code signing policy](CODE_SIGNING.md)

---

## 📖 I. TỔNG QUAN HỆ THỐNG

**AutoGuardian** là một giải pháp phần mềm thị giác máy tính toàn diện chạy trên máy tính (Desktop Application), được thiết kế để giám sát giao thông đô thị và quản lý bãi đỗ xe thông minh theo thời gian thực (Real-time).

Ứng dụng tiếp nhận luồng video từ **File video (`.mp4`, `.avi`, `.mkv`)**, **Webcam trực tiếp (USB/Built-in)** hoặc **Camera IP chuẩn RTSP**, áp dụng mô hình Deep Learning **YOLOv8** kết hợp thuật toán theo dõi **ByteTrack** để thực hiện:
* **Phát hiện & Bám vết đối tượng phương tiện (Vehicle Detection & Tracking):** Đánh `Track ID` duy nhất cho từng xe (`car`, `motorcycle`, `bus`, `truck`).
* **Ước lượng tốc độ xe theo thời gian thực (Speed Estimation - km/h):** Tính toán vận tốc di chuyển tức thời dựa trên khoảng cách mét/pixel và thời gian thực tế, hiển thị trực tiếp trên bounding box.
* **Nhận diện biển số xe tự động (ANPR/ALPR) bằng Deep Learning, chạy tốt trên CPU:** Hai tầng ONNX Runtime: mô hình YOLOv9 định vị biển số trong khung xe (`open-image-models`), sau đó mô hình OCR biển số đa quốc gia (`fast-plate-ocr`, 65 khu vực gồm Việt Nam, Anh, EU, Mỹ...) đọc ký tự kèm độ tin cậy từng ký tự. Mỗi xe được đọc nhiều lần khi tiến lại gần camera và bỏ phiếu theo độ tin cậy; chỉ biển số đạt ngưỡng tin cậy (mặc định 0.9) mới được hiển thị - **không bao giờ tự bịa biển số** khi ảnh quá mờ/nhỏ.
* **Danh sách biển số xe Real-time (Live Plate Feed):** Hiển thị danh sách xe vừa đi qua kèm ảnh crop thumbnail biển số sắc nét, biển số nhận diện, vận tốc xe và thời gian.
* **Đếm lưu lượng xe qua vạch ảo (Virtual Line Crossing Analytics):** Dùng phép toán Tích hướng (Cross-Product) và giao cắt vector; **bảo đảm mỗi Track ID chỉ được đếm đúng 1 lần duy nhất** trong suốt chu kỳ xuất hiện.
* **Phát hiện đỗ xe trái phép trong vùng cấm (Parking Violation Analytics):** Kiểm tra vị trí xe trong đa giác ROI (`Point-in-polygon`). Nếu xe đứng yên trong vùng cấm quá thời gian ngưỡng ($T_{stay} > T_{threshold}$, mặc định 30 giây) và độ dịch chuyển $\Delta d < \epsilon$, hệ thống tự động kích hoạt còi báo, nhấp nháy màn hình và chụp ảnh bằng chứng vi phạm.
* **Ghi hình & Xuất Báo cáo:** Tự động cắt ảnh vi phạm độ nét cao `VIPHAM_[TrackID]_[YYYYMMDD_HHMMSS].jpg`, hỗ trợ ghi video luồng xử lý kèm biểu tượng `REC`, lưu trữ cơ sở dữ liệu SQLite và trích xuất báo cáo Excel (`.xlsx`) đa sheet và CSV (có Biển số và Vận tốc).

---

## 🏛 II. KIẾN TRÚC HỆ THỐNG & CÔNG NGHỆ

### 1. Kiến trúc Đa luồng (Multi-threading Architecture)
Để đảm bảo giao diện không bao giờ bị treo ("Not Responding") khi chạy AI nặng, AutoGuardian phân tách hoàn toàn các luồng hoạt động:
* **UI Thread (Main GUI Thread):** Xử lý giao diện người dùng PyQt5, tương tác chuột vẽ vạch/vùng đa giác, hiển thị video.
* **Streaming Worker Thread:** Đọc luồng video độc lập (`cv2.VideoCapture`), đẩy khung hình vào hàng đợi FIFO có cơ chế **Frame Dropping chủ động** (giới hạn 2–3 frames) để triệt tiêu độ trễ latency. Tự động kết nối lại RTSP sau mỗi 5 giây nếu đứt mạng.
* **AI Processing Worker Thread (`QThread`):** Chạy tiền xử lý, suy luận YOLOv8, bám vết ByteTrack, phân tích hình học vạch đếm & ROI cấm đỗ, vẽ overlay.
* **Storage Thread / I/O:** Ghi log SQLite, chụp lưu ảnh vi phạm và ghi video `VideoWriter` an toàn tài nguyên.

```mermaid
flowchart LR
    subgraph Input [Nguồn Dữ Liệu]
        CAM[Webcam / RTSP / Video File]
    end

    subgraph Streaming [MOD-02: Streaming Module]
        VR[VideoReader Background Thread]
        FQ[FrameQueueManager - Auto Drop Oldest]
    end

    subgraph CoreAI [MOD-03: Core AI Module]
        DET[YOLOv8 Vehicle Detector]
        TRK[ByteTrack Persistent Tracker]
        LC[Line Crossing Counter - Cross Product]
        PA[Parking Violation Analyzer - ROI Polygon]
        ENG[AutoGuardian AI Engine]
    end

    subgraph GUI [MOD-01: PyQt5 GUI Module]
        MW[Main Window Dashboard]
        CV[Interactive Video Canvas]
        EV[Evidence Viewer Dialog]
    end

    subgraph Storage [MOD-04: Storage Module]
        DB[(SQLite Database)]
        SNAP[Captures / Evidence .jpg]
        REC[Video Recorder .mp4]
        EXP[Excel / CSV Reports]
    end

    CAM --> VR
    VR --> FQ
    FQ --> ENG
    ENG --> DET --> TRK
    TRK --> LC & PA
    ENG --> MW & CV
    LC & PA --> DB
    PA --> SNAP
    ENG --> REC
    DB --> EXP
```

### 2. Danh mục Tech Stack
* **Ngôn ngữ:** Python 3.11 (hoặc Python 3.10+)
* **Thị giác Máy tính:** `ultralytics` (YOLOv8), `opencv-python`, `torch`, `torchvision`, `lap` (ByteTrack)
* **Nhận diện biển số:** `onnxruntime`, `open-image-models` (YOLOv9 plate detector), `fast-plate-ocr` (OCR đa quốc gia)
* **Thiết bị suy luận:** tự động dùng GPU NVIDIA nếu có, nếu không tự chuyển sang CPU (`"device": "auto"` trong `configs/config.json`)
* **Giao diện người dùng (GUI):** `PyQt5` (Dark Theme chuyên nghiệp, Interactive Canvas)
* **Đại số tuyến tính & Hình học:** `numpy`, `scipy`, `scikit-learn`
* **Lưu trữ & Báo cáo:** `sqlite3`, `pandas`, `openpyxl`

---

## 🗂 III. CẤU TRÚC DỰ ÁN

```text
AutoGuardian/
├── assets/                  # Tài nguyên tĩnh (icons, styles, test media)
├── configs/
│   ├── config.json          # File cấu hình hệ thống, AI, ngưỡng thời gian, storage
│   └── zones.json           # Tọa độ vạch ảo và vùng đa giác cấm đỗ ROI
├── models/
│   ├── yolov8n.pt           # Trọng số mô hình YOLOv8 pre-trained
│   └── plates/              # Mô hình ONNX định vị biển số (YOLOv9) + OCR biển số
├── outputs/
│   ├── captures/            # Ảnh chụp bằng chứng xe vi phạm (.jpg)
│   ├── recordings/          # Video ghi hình luồng output (.mp4, .avi)
│   └── reports/             # Báo cáo thống kê (.xlsx, .csv)
├── src/
│   ├── core/
│   │   ├── detector.py      # Bộ nhận diện xe hơi YOLOv8 và trích xuất bbox
│   │   ├── line_counter.py  # Logic đếm xe qua vạch (Cross-product, đếm duy nhất 1 lần)
│   │   ├── parking_analyzer.py # Logic cảnh báo đỗ xe trái phép trong vùng đa giác ROI
│   │   ├── plate_recognizer.py # Định vị + OCR biển số (ONNX), bỏ phiếu nhiều khung hình
│   │   └── engine.py        # Bộ điều phối AI Engine hợp nhất
│   ├── gui/
│   │   ├── canvas.py        # Canvas hiển thị video & tương tác chuột vẽ vạch/ROI
│   │   ├── dialogs.py       # Hộp thoại phóng to ảnh vi phạm, cấu hình RTSP/ROI
│   │   ├── worker.py        # QThread Worker điều phối streaming và AI ngầm
│   │   └── main_window.py   # Cửa sổ chính giao diện Dark Theme
│   ├── streaming/
│   │   ├── queue_manager.py # Hàng đợi FIFO có cơ chế Frame Dropping chống trễ
│   │   └── video_reader.py  # Bộ đọc video đa nguồn & tự động kết nối lại RTSP
│   ├── storage/
│   │   ├── database.py      # Quản lý SQLite database lưu vết sự kiện đếm và vi phạm
│   │   ├── evidence.py      # Quản lý cắt và lưu ảnh bằng chứng vi phạm
│   │   ├── recorder.py      # Quản lý ghi hình video output (VideoWriter)
│   │   └── exporter.py      # Xuất báo cáo Excel đa sheet và CSV
│   └── utils/
│       ├── config.py        # Bộ đọc và lưu file cấu hình JSON
│       ├── constants.py     # Định nghĩa các hằng số màu sắc, kích thước (loại bỏ Magic Numbers)
│       ├── drawing.py       # Bộ tiện ích vẽ bounding box, vạch đếm, đa giác bán trong suốt
│       └── geometry.py      # Thuật toán hình học tính tâm, tích hướng, point-in-polygon
├── tests/
│   ├── test_core_engine.py  # Kiểm thử detector, line counter, parking analyzer
│   ├── test_e2e_pipeline.py # Kiểm thử luồng tích hợp End-to-End toàn diện
│   ├── test_gui.py          # Kiểm thử các widget và giao diện PyQt5
│   ├── test_storage_and_utils.py # Kiểm thử SQLite, exporter, geometry, drawing
│   └── test_streaming.py    # Kiểm thử bộ đọc video và hàng đợi frame dropping
├── launcher/
│   └── autoguardian_launcher.py # Bộ cài nhẹ: phát hiện GPU, tải gói CPU/GPU từ GitHub Release
├── tools/
│   ├── package_release.py   # Nén + chia phần < 2 GB cho GitHub Release
│   └── make_manifest.py     # Tạo manifest.json (URL, kích thước, SHA-256 các gói) cho launcher
├── docs/images/             # Ảnh minh họa cho hướng dẫn sử dụng
├── app.py                   # Điểm khởi chạy chính của ứng dụng
├── build_exe.ps1            # Script đóng gói thành AutoGuardian.exe (PyInstaller)
├── build_launcher.ps1       # Script build AutoGuardian-Setup.exe + manifest.json
├── requirements.txt         # Danh sách thư viện phụ thuộc
├── requirements-nodeps.txt  # Thư viện biển số (cài với --no-deps)
├── HUONG_DAN_SU_DUNG.md     # Hướng dẫn sử dụng cho người dùng cuối
└── README.md                # Tài liệu hướng dẫn
```

---

## 🚀 IV. HƯỚNG DẪN CÀI ĐẶT & KHỞI CHẠY

> **Người dùng cuối (không cần Python):** tải `AutoGuardian-Setup.exe` tại trang
> [Releases](https://github.com/NguyenMinhPhuc/pro-dem-va-tinh-van-toc/releases/latest) – bộ cài tự chọn bản GPU/CPU
> phù hợp. Xem chi tiết trong **[HƯỚNG DẪN SỬ DỤNG](HUONG_DAN_SU_DUNG.md)**. Các mục dưới đây dành cho nhà phát triển.

### 1. Yêu cầu Hệ thống
* Hệ điều hành: Windows 10/11, Linux, hoặc macOS
* Python: Phiên bản **3.10** hoặc **3.11** (khuyến nghị dùng CPython 3.11)
* Trình quản lý gói: `uv` (cực nhanh) hoặc `pip` tiêu chuẩn

### 2. Cài đặt Môi trường
Mở Terminal hoặc PowerShell tại thư mục dự án:

```powershell
# Cách 1: Sử dụng uv (Khuyến nghị, cài đặt trong vài giây)
uv venv --python 3.11 .venv
.venv\Scripts\activate
uv pip install -r requirements.txt
uv pip install --no-deps -r requirements-nodeps.txt

# Cách 2: Sử dụng venv và pip truyền thống
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pip install --no-deps -r requirements-nodeps.txt
```

> Muốn dùng GPU NVIDIA khi chạy từ mã nguồn: cài PyTorch bản CUDA trước, ví dụ
> `pip install torch torchvision --index-url https://download.pytorch.org/whl/cu124`.

### 3. Khởi chạy Ứng dụng
```powershell
# Chạy ứng dụng thông qua môi trường ảo:
.venv\Scripts\python.exe app.py
```

### 4. Đóng gói thành file EXE (Windows)
```powershell
# Bản CPU (mặc định): chạy trên mọi máy Windows x64, có hoặc không có GPU
powershell -ExecutionPolicy Bypass -File build_exe.ps1

# Bản CUDA (tùy chọn, rất nặng ~4 GB): tận dụng GPU NVIDIA, vẫn tự chạy CPU nếu máy không có GPU
powershell -ExecutionPolicy Bypass -File build_exe.ps1 -Cuda
```
Kết quả nằm ở `dist\cpu\AutoGuardian\` hoặc `dist\cuda\AutoGuardian\`, kèm file nén trong `dist\` (tự chia thành
`.zip.001`, `.zip.002`... nếu lớn hơn 1.9 GB - giải nén bằng 7-Zip, mở file `.001`). Copy nguyên thư mục sang máy khác,
chạy `AutoGuardian.exe` - không cần cài Python. Cấu hình ở `configs\`, kết quả ở `outputs\`, log lỗi ở `outputs\logs\autoguardian.log`.

### 5. Phát hành qua bộ cài (Launcher)
Người dùng chỉ tải `AutoGuardian-Setup.exe` (~10 MB). Khi chạy, bộ cài đọc
`https://github.com/<repo>/releases/latest/download/manifest.json`, phát hiện GPU NVIDIA (`nvidia-smi`), tải gói
CPU hoặc GPU (tải tiếp khi đứt mạng, kiểm tra SHA-256), giải nén vào `%LOCALAPPDATA%\AutoGuardian`, tạo shortcut và
những lần sau tự kiểm tra bản cập nhật (giữ nguyên `configs\` và `outputs\` của người dùng).
```powershell
# 1. Build hai gói ứng dụng (mục 4), upload các file trong dist\ lên release chứa gói, ví dụ v1.1.0
# 2. Build bộ cài + manifest trỏ tới release chứa gói
powershell -ExecutionPolicy Bypass -File build_launcher.ps1 -AppVersion 1.1.0 -PackageTag v1.1.0
# 3. Tạo release mới nhất (Latest) gồm dist\AutoGuardian-Setup.exe và dist\manifest.json
```
Tham số bộ cài: `--variant cpu|cuda` (bỏ qua màn hình chọn), `--reinstall`, `--no-launch`, `--no-shortcuts`,
`--no-update-check`.

### 6. Phát hành tự động & ký số (GitHub Actions + SignPath Foundation)
Workflow [`.github/workflows/release.yml`](.github/workflows/release.yml) build toàn bộ trên GitHub Actions
(bản CPU, bản CUDA, bộ cài, chạy test), gửi `AutoGuardian-Setup.exe` và `AutoGuardian.exe` sang SignPath ký số,
rồi mới đóng gói, tạo `manifest.json` và phát hành 2 release: `vX.Y.Z` (Latest, bộ cài) và `packages-vX.Y.Z`
(Pre-release, các gói launcher tự tải).
```powershell
git tag v1.3.0; git push origin v1.3.0      # build + ký + phát hành
# hoặc tab Actions -> Release -> Run workflow (bỏ chọn "publish" để chỉ build thử)
```
Bước ký chỉ chạy khi đã cấu hình SignPath (biến repo `SIGNPATH_ORGANIZATION_ID`, secret `SIGNPATH_API_TOKEN`;
tuỳ chọn `SIGNPATH_PROJECT_SLUG`, `SIGNPATH_SIGNING_POLICY_SLUG`, `SIGNPATH_ARTIFACT_CONFIGURATION_SLUG`).
Cấu hình artifact cho SignPath: [`.signpath/artifact-configuration.xml`](.signpath/artifact-configuration.xml).
Chính sách ký số: [CODE_SIGNING.md](CODE_SIGNING.md).

---

## 🎮 V. HƯỚNG DẪN VẬN HÀNH CÁC TÍNH NĂNG

### 1. Chọn Nguồn Video (Input Source)
* **Tải File Video:** Bấm nút **"📁 Chọn Video"** để mở hộp thoại và nạp file video mẫu (`.mp4`, `.avi`, `.mkv`).
* **Sử dụng Webcam:** Chọn cổng Webcam (0, 1 hoặc 2) trong dropdown menu và bấm **"📹 Mở Webcam"**.
* **Kết nối Camera IP (RTSP):** Bấm **"🌐 Kết nối Camera IP (RTSP)"**, nhập URL luồng RTSP (ví dụ: `rtsp://admin:123456@192.168.1.100:554/stream1`) và bấm OK. Nếu mất mạng, hệ thống sẽ tự động thử kết nối lại sau mỗi 5 giây mà không làm treo app.

### 2. Vẽ & Điều chỉnh Vạch Đếm và Vùng Cấm Đỗ Trực Tiếp
* **Vẽ Vạch Đếm Xe:**
  1. Bấm nút **"✏️ Vẽ Vạch Đếm"**. Con trỏ chuột chuyển thành hình chữ thập.
  2. Nhấp chuột trái tại điểm bắt đầu $P_1$, kéo đến điểm kết thúc $P_2$ và thả chuột.
  3. Vạch đếm màu vàng sẽ xuất hiện ngay lập tức trên màn hình và bộ đếm sẽ tự động cập nhật tọa độ mới.
* **Vẽ Vùng Cấm Đỗ (Polygon ROI):**
  1. Bấm nút **"📐 Vẽ Vùng Cấm Đỗ"**.
  2. Nhấp chuột trái để tạo lần lượt các đỉnh của đa giác (tối thiểu 3 đỉnh).
  3. **Nhấp đúp chuột** hoặc **nhấp chuột phải** để hoàn tất việc khép kín đa giác.
  4. Vùng đa giác màu xanh lá cây bán trong suốt sẽ xuất hiện. Nếu có xe đỗ quá giờ, vùng này sẽ tự động chuyển sang màu đỏ rực.
* **Đo Tốc Độ Chuẩn Xác 2 Làn Ra/Vào Bằng Mốc Chuẩn (Dual-Lane Speed Trap):**
  1. **Tự động áp dụng Mốc Mặc Định:** Ngay khi khởi động mà người dùng chưa vẽ bất kỳ mốc nào, hệ thống tự động tải bộ tọa độ mốc chuẩn cho cả **Làn Vào (IN)** và **Làn Ra (OUT)** (khoảng cách chuẩn 20m), xe chạy qua bất kỳ làn nào cũng được đo tốc độ ngay lập tức!
  2. **Chọn làn cấu hình:** Chọn `🚗 Làn Vào (IN)` hoặc `🚙 Làn Ra (OUT)` trong menu chọn làn trên thanh công cụ.
  3. Bấm **"🚩 Vẽ Mốc A"**: Kéo chuột để đặt vạch mốc bắt đầu tính giờ $t_A$ cho làn đó.
  4. Bấm **"🏁 Vẽ Mốc B"**: Kéo chuột để đặt vạch mốc kết thúc tính giờ $t_B$ cho làn đó.
  5. Bấm **"📏 Khoảng Cách"**: Nhập cự ly thực tế giữa hai mốc tính bằng mét riêng cho làn đó (ví dụ: $20.0$m hoặc $50.0$m).
  6. Bấm **"↺ Mặc Định"**: Khôi phục lại toàn bộ tọa độ và khoảng cách mốc chuẩn ban đầu cho cả 2 làn bất cứ lúc nào.
  7. Khi xe chạy từ Mốc A qua Mốc B trên làn tương ứng, hệ thống đo chính xác thời gian quá cảnh $\Delta t = |t_B - t_A|$ và tính vận tốc chuẩn ITS $v = \frac{D}{\Delta t} \times 3.6$ (km/h), triệt tiêu hoàn toàn sai số phối cảnh cao tốc.
* **Cập nhật Vận Tốc Real-time lên Bảng Biển Số (Live Speed Update):**
  * Danh sách biển số tự động chuyển từ trạng thái `"Đang đo..."` sang vận tốc thực tế (ví dụ: `88.5 km/h` - màu xanh lá cây) ngay khi hệ thống tính toán xong vận tốc của phương tiện đó.
* **Cài đặt Ngưỡng Thời Gian Đỗ:**
  * Bấm nút **"⚙️ Cài Ngưỡng Đỗ"** để nhập số giây tối đa cho phép đỗ xe (mặc định 30 giây) và ngưỡng sai số dịch chuyển đứng yên (mặc định 20 pixel).

### 3. Tinh chỉnh Tham số AI & Các Lớp Hiển thị
* **Ngưỡng Độ tin cậy ($Conf$):** Kéo thanh trượt để thay đổi giá trị từ `0.10` đến `0.95`. Giá trị áp dụng tức thì lên luồng nhận diện.
* **Ẩn/Hiện Lớp thông tin:** Tích chọn hoặc bỏ chọn độc lập các checkbox:
  * `Bounding Box`: Khung chứa quanh xe
  * `Track ID`: Mã số định danh xe
  * `Hiển thị FPS`: Tốc độ xử lý khung hình/giây
  * `Vạch Đếm Ảo`: Đường vạch kiểm tra cắt ngang
  * `Vùng Cấm Đỗ (ROI)`: Vùng đa giác giám sát đỗ xe

### 4. Bảng Chỉ Số Giám Sát Real-time & Cảnh Báo
* **Dashboard:** Thẻ thống kê cập nhật trực tiếp:
  * **Tổng Xe Đếm:** Số lượng xe đã đi qua vạch
  * **Chiều Vào (IN) / Chiều Ra (OUT):** Phân loại theo hướng di chuyển
  * **Vi Phạm Đỗ Xe:** Tổng số lượt phương tiện vi phạm
  * **Tốc Độ FPS:** Hiệu năng xử lý thực tế
  * **Xe Trong Vùng Cấm:** Số lượng phương tiện hiện đang nằm trong ROI
* **Cảnh báo âm thanh & Biểu ngữ:** Khi phát hiện vi phạm, biểu ngữ chuyển sang màu đỏ cảnh báo, còi bip phát ra (nếu bật chuông) và hệ thống tự động chụp ảnh bằng chứng.
* **Thử nghiệm:** Bấm **"🔔 Thử Âm Thanh"** để kiểm tra loa/chuông cảnh báo.

### 5. Xem Bằng Chứng Vi Phạm & Truy Xuất Dữ Liệu
* **Xem Bằng Chứng:** Bảng phía dưới liệt kê toàn bộ các sự kiện vi phạm. **Nhấp đúp vào bất kỳ dòng nào** để mở hộp thoại phóng to ảnh chụp bằng chứng (Snapshot có khoanh vùng đỏ xe vi phạm, nhãn thời gian và Track ID), cùng nút mở trực tiếp thư mục chứa file trên ổ đĩa.
* **Ghi Hình Video (REC):** Bấm nút **"⏺ Ghi hình (REC)"** để lưu lại toàn bộ luồng video đã vẽ overlay vào thư mục `outputs/recordings/`. Biểu tượng chấm đỏ `REC` sẽ nhấp nháy ở góc phải màn hình. Bấm lại để dừng và lưu tệp.
* **Đặt Lại Bộ Đếm (Reset Counter):** Bấm **"🔄 Reset Counter"** và xác nhận trên hộp thoại để xóa toàn bộ số liệu đếm, làm mới danh sách ID và xóa bảng vi phạm về 0.
* **Trích Xuất Báo Cáo:**
  * **Xuất Excel:** Bấm **"📊 Xuất Excel"** để xuất tệp đa sheet gồm sheet `Lưu lượng xe đếm` và sheet `Sự kiện vi phạm`.
  * **Xuất CSV:** Bấm **"📄 Xuất CSV"** để xuất file dữ liệu định dạng chuẩn UTF-8 có BOM đọc tiếng Việt không lỗi font.

---

## 🧪 VI. KIỂM THỬ HỆ THỐNG (UNIT & INTEGRATION TESTS)

Hệ thống đi kèm bộ kiểm thử tự động toàn diện bao phủ 100% các mô-đun. Để chạy toàn bộ test suite:

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py"
```

**Kết quả kiểm thử:**
```text
Ran 19 tests in 8.042s
OK
```

| Tệp Kiểm Thử | Nội dung kiểm thử | Trạng thái |
| :--- | :--- | :---: |
| `tests/test_storage_and_utils.py` | Kiểm thử SQLite đa luồng, xuất báo cáo Excel/CSV, thuật toán hình học Tích hướng & Point-in-polygon, bộ tiện ích vẽ overlay. | **PASS** |
| `tests/test_streaming.py` | Kiểm thử cơ chế Frame Dropping khi hàng đợi đầy, bộ đọc video VideoReader đọc file, webcam, lặp lại video liên tục và giải phóng tài nguyên. | **PASS** |
| `tests/test_core_engine.py` | Kiểm thử nhận diện YOLOv8, kiểm thử đếm xe qua vạch đảm bảo mỗi Track ID chỉ đếm 1 lần, kiểm thử đo thời gian đỗ xe vi phạm. | **PASS** |
| `tests/test_speed_and_plate.py` | Kiểm thử ước lượng vận tốc xe (Speed Estimator km/h), module SpeedTrapZone 2 mốc chuẩn, module nhận diện biển số xe (License Plate Recognizer) và cơ chế lưu trữ biển số vào database. | **PASS** |
| `tests/test_gui.py` | Kiểm thử giao diện PyQt5, tương tác chuột trên Canvas (Vẽ Vạch, ROI, Mốc A, Mốc B), cập nhật vận tốc thời gian thực vào bảng biển số, các hộp thoại SnapshotViewer, ROIConfig, RTSPInput, Tab biển số real-time và MainWindow. | **PASS** |
| `tests/test_e2e_pipeline.py` | Kiểm thử tích hợp toàn diện chu trình End-to-End từ nạp frame $\rightarrow$ AI $\rightarrow$ Đếm vạch $\rightarrow$ Nhận diện biển số & Tốc độ $\rightarrow$ Báo động đỗ xe $\rightarrow$ Chụp ảnh $\rightarrow$ Ghi video REC $\rightarrow$ Xuất báo cáo. | **PASS** |

---

## 📋 VII. BẢNG CHECKLIST DEFINITION OF DONE (DoD)

Dự án AutoGuardian đã thỏa mãn 100% các tiêu chuẩn phát triển khắt khe trong `.skill/AI-development-rules.md`:

- [x] **Không chứa Magic Numbers:** Tất cả các hằng số màu sắc, kích thước frame, font, ngưỡng thời gian vi phạm, cổng mạng đều được khai báo rõ ràng trong `src/utils/constants.py` hoặc file cấu hình `configs/config.json`.
- [x] **Xử lý Ngoại lệ An toàn:** 100% thao tác I/O (Đọc/Ghi file, Camera RTSP, SQLite Database, VideoWriter) đều được bảo vệ trong khối `try...except...finally` chặt chẽ, không bao giờ dùng bare `except: pass`.
- [x] **Tách biệt Triệt để Logic và Giao diện:** Logic AI, Tracking và Xử lý hình học (`src/core/`, `src/utils/`) độc lập hoàn toàn với các widget giao diện PyQt5 (`src/gui/`).
- [x] **Quản lý Tài nguyên & Bộ nhớ:** VideoCapture và VideoWriter được release an toàn khi dừng luồng; cơ chế Frame Dropping chủ động ngăn chặn rò rỉ RAM khi xử lý video thời gian thực.
- [x] **Đầy đủ Type Hinting & Docstrings:** Mọi class và hàm/phương thức đều có Type Annotation và Google-style docstring chi tiết.

---

*AutoGuardian - An toàn, Thông minh và Hiệu năng cao.*


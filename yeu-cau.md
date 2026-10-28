# TÀI LIỆU PHÂN TÍCH VÀ THIẾT KẾ HỆ THỐNG AUTOGUARDIAN
> **Chủ đề:** Nhận diện đối tượng xe hơi trong ảnh và video real-time  
> **Học phần:** Thị giác máy tính (Computer Vision)  
> **Ứng dụng:** AutoGuardian - Hệ thống Giám sát & Bãi đỗ xe Thông minh  

---

## PHẦN 1: PHÂN TÍCH CHỦ ĐỀ TRONG HỌC PHẦN THỊ GIÁC MÁY TÍNH

Nhận diện xe hơi (Car/Vehicle Detection) là bài toán kinh điển mang tính ứng dụng thực tế cao, bao hàm đầy đủ các kiến thức cốt lõi của môn học Thị giác máy tính:

1. **Bài toán Phát hiện Đối tượng (Object Detection):**
   * **Xác định vị trí (Localization):** Trả về tọa độ khung chứa (Bounding Box $[x, y, w, h]$).
   * **Phân loại (Classification):** Xác định đối tượng thuộc nhãn `car` / `vehicle` với độ tin cậy (Confidence score).

2. **Các thách thức kỹ thuật tiêu biểu:**
   * **Biến đổi góc nhìn & Kích thước (Scale & Occlusion):** Xe ở xa rất nhỏ, xe ở gần rất lớn, hoặc xe bị che khuất một phần.
   * **Điều kiện ánh sáng:** Ban ngày, đêm thiếu sáng, sương mù, mưa, hoặc đèn xe gây chói.
   * **Tốc độ xử lý Real-time:** Đảm bảo tốc độ xử lý đạt từ 25–30 FPS trở lên để không bị trễ khung hình khi dùng Webcam/IP Camera.

---

## PHẦN 2: Y TƯỞNG SẢN PHẦM PHẦN MỀM

### 💡 Tên ứng dụng: **AutoGuardian - Hệ thống Giám sát & Bãi đỗ xe Thông minh Real-time**

### 1. Mô tả Ý tưởng
**AutoGuardian** là một phần mềm ứng dụng thị giác máy tính chạy trên máy tính (Desktop App). Phần mềm tiếp nhận nguồn vào trực tiếp từ **Camera live** (Webcam, IP Camera RTSP) hoặc **File video (.mp4, .avi)**. 

Hệ thống phân tích từng khung hình theo thời gian thực để:
* Phát hiện và theo dõi vị trí xe hơi (Vehicle Detection & Tracking).
* Đếm lưu lượng xe ra/vào hoặc đi qua một vạch kẻ ranh giới giả lập (Virtual Line Crossing).
* Phát hiện trạng thái đỗ xe sai quy định hoặc cảnh báo ùn tắc giao thông cục bộ trong khu vực giám sát.
* Hiển thị giao diện điều khiển trực quan bao gồm khung hình xử lý, thông số FPS, số lượng xe và bảng điều khiển tải file/chọn nguồn camera.

### 2. Mục tiêu Ý tưởng

#### a. Mục tiêu chung
* Xây dựng một ứng dụng phần mềm hoàn chỉnh áp dụng kỹ thuật Thị giác máy tính để phát hiện, đếm và giám sát xe hơi theo thời gian thực từ nguồn Video/Camera với độ chính xác và độ mượt cao.

#### b. Mục tiêu chi tiết
* **Xử lý đa nguồn vào:** Tiếp nhận mượt mà cả file video (.mp4) lẫn luồng camera thực tế (RTSP/Webcam).
* **Đảm bảo hiệu năng Real-time:** Đạt tốc độ xử lý tối thiểu **30 FPS** trên GPU phổ thông hoặc từ **15–20 FPS** trên CPU.
* **Độ chính xác cao:** Đạt độ chính xác nhận diện xe (mAP@0.5) **> 85%** trong điều kiện ánh sáng tiêu chuẩn.
* **Tích hợp Tracking & Counting:** Đánh ID duy nhất cho từng xe bằng thuật toán ByteTrack/DeepSORT để tránh đếm lặp.
* **Giao diện người dùng (GUI):** Thân thiện, dễ vận hành, cho phép bật/tắt vạch đếm xe và xuất báo cáo lưu lượng.

### 3. Đánh giá Công nghệ Sử dụng

| Công nghệ / Thư viện | Vai trò trong hệ thống | Đánh giá ưu điểm | Đánh giá hạn chế & Giải pháp |
| :--- | :--- | :--- | :--- |
| **Python 3.x** | Ngôn ngữ lập trình chính | Tốc độ phát triển nhanh; Hệ sinh thái AI/Data Science phong phú nhất hiện nay. | Tốc độ thực thi thuần túy chậm hơn C++. *(Giải pháp: Dùng các thư viện C++ binding như OpenCV, PyTorch/TensorRT)*. |
| **YOLOv8 (Ultralytics)** | Mô hình Nhận diện Đối tượng | Tốc độ xử lý cực nhanh, độ chính xác SOTA. Cung cấp sẵn các phiên bản nhỏ nhẹ (`yolov8n.pt`, `yolov8s.pt`). Pre-train sẵn trên tập COCO (chứa nhãn `car`). | Cần GPU (CUDA) để đạt hiệu năng tối đa khi dùng model lớn. *(Giải pháp: Xuất mô hình sang ONNX/OpenVINO khi chạy trên CPU)*. |
| **OpenCV** | Thư viện Xử lý Ảnh & Video | Đọc/ghi luồng video, camera tối ưu. Hỗ trợ vẽ Bounding Box, vạch đếm, text. | Quản lý bộ nhớ luồng đọc frame cần cẩn thận để tránh leak memory. |
| **PyQt5 / CustomTkinter** | Lập trình Giao diện (GUI) | Đóng gói phần mềm thành ứng dụng chuyên nghiệp. Phân tách luồng xử lý AI (Threading) và luồng hiển thị GUI. | Cần kiến thức về Multi-threading để GUI không bị "Not Responding". |

### 4. Đánh giá Khả năng Áp dụng & Tính Khả thi

#### a. Tính khả thi trong phạm vi Học phần
* **Khả thi 100%:** YOLOv8 đã pre-train sẵn trên COCO dataset (đã có lớp `car`), không bắt buộc phải tốn hàng tuần để gom dataset và train lại từ đầu.
* **Phù hợp kiến thức môn học:** Đồ án vừa thể hiện được kỹ năng xử lý video (OpenCV), kỹ năng ứng dụng mô hình AI hiện đại (YOLOv8), vừa thể hiện tư duy đóng gói sản phẩm phần mềm.

#### b. Khả năng phát triển thương mại / thực tế
* **Ứng dụng quản lý bãi đỗ xe thông minh:** Tự động phát hiện vị trí trống, đếm số lượng xe trong bãi.
* **Giám sát giao thông đô thị (ITS):** Đo lưu lượng giao thông theo giờ, phát hiện xe đi sai làn, đỗ xe trái phép.
* **Tích hợp thiết bị biên (Edge AI):** Đóng gói chạy trên NVIDIA Jetson Nano hoặc Raspberry Pi 4 để lắp đặt trực tiếp tại giao lộ.

---

## PHẦN 3: TÁC NHÂN VÀ HÀNH VI CỦA TÁC NHÂN

### 1. Quản trị viên / Người vận hành (Operator/Admin)
* **Quản lý nguồn vào:** Chọn nguồn dữ liệu (Live Camera RTSP/Webcam hoặc File Video `.mp4`). Phát / Tạm dừng / Dừng luồng.
* **Cấu hình tham số:** Điều chỉnh ngưỡng độ tin cậy ($Conf$). Vẽ/Thiết lập vạch đếm ảo và vùng cấm đỗ (ROI). Bật/Tắt các chế độ hiển thị overlay.
* **Giám sát & Khai thác:** Theo dõi luồng video real-time, quan sát chỉ số thống kê, nhận cảnh báo vi phạm và xuất báo cáo (Excel/CSV).

### 2. Nguồn vào Video (Camera / Video File)
* **Cung cấp luồng khung hình (Frame Streaming):** Liên tục gửi khung hình thô (Raw RGB) theo chuẩn FPS đến OpenCV.
* **Tự động kết nối lại (Re-connection):** Tự động phát hiện sự cố ngắt kết nối mạng và kết nối lại luồng RTSP.

### 3. Bộ xử lý AI (AI Detection & Tracking Engine)
* **Tiền xử lý dữ liệu:** Resize khung hình (vd: $640 \times 640$), chuẩn hóa dải pixel.
* **Phát hiện đối tượng (YOLOv8):** Phân tích và trích xuất Bounding Box, nhãn `car` và score.
* **Theo dõi đối tượng (ByteTrack/DeepSORT):** Gán `Track ID` duy nhất cho từng xe.
* **Tính toán Logic:** Kiểm tra giao cắt vạch đếm (Line Crossing) và thời gian đứng yên trong vùng cấm (Parking Violation).
* **Hậu xử lý:** Vẽ Bounding Box, Track ID, vạch đếm lên khung hình.

### 4. Hệ thống Lưu trữ & Báo cáo (Storage System)
* **Ghi nhận sự kiện:** Tự động ghi log sự kiện đếm xe / vi phạm.
* **Lưu trữ bằng chứng:** Chụp ảnh/cắt clip làm bằng chứng khi phát hiện xe đỗ sai quy định.
* **Xuất báo cáo:** Đóng gói dữ liệu thống kê đếm xe ra `.csv` / `.xlsx`.

---

## PHẦN 4: DANH SÁCH USER STORIES KÈM ACCESSTANT CRITERIA (AC)

### 1. Nhóm User Story cho Tác nhân: Quản trị viên / Người vận hành (Operator/Admin)

* **US-01: Chọn nguồn dữ liệu đầu vào**
  * *User Story:* Là một **Người vận hành**, tôi muốn **chọn nguồn video đầu vào giữa File `.mp4` và Live Camera (Webcam/RTSP)**, để **hệ thống linh hoạt xử lý video có sẵn hoặc giám sát trực tiếp.**
  * *AC1:* Giao diện cung cấp tùy chọn rõ ràng: "Tải file video" và "Kết nối Camera".
  * *AC2:* Chọn "Tải file video" mở hộp thoại chọn định dạng `.mp4`, `.avi`, `.mkv`.
  * *AC3:* Chọn "Kết nối Camera" cho phép chọn Webcam (ID: 0, 1) hoặc nhập đường dẫn RTSP.
  * *AC4:* Hiển thị thông báo lỗi thân thiện nếu không kết nối được nguồn.

* **US-02: Thiết lập vạch đếm ảo và vùng giám sát (ROI)**
  * *User Story:* Là một **Người vận hành**, tôi muốn **vẽ và điều chỉnh vạch đếm ảo trực tiếp trên màn hình**, để **định hình chính xác khu vực đếm xe hoặc giám sát.**
  * *AC1:* Cho phép nhấp/kéo chuột để tạo vạch đếm (hoặc vùng ROI dạng đa giác) trên khung hình preview.
  * *AC2:* Cho phép xóa, vẽ lại hoặc di chuyển vạch mà không làm dừng hoặc treo ứng dụng.
  * *AC3:* Tọa độ vạch/ROI được lưu tự động để bộ xử lý AI tính toán.

* **US-03: Điều chỉnh ngưỡng độ tin cậy (Confidence Threshold)**
  * *User Story:* Là một **Người vận hành**, tôi muốn **thay đổi ngưỡng độ tin cậy ($Conf$) qua thanh trượt**, để **tối ưu hóa độ chính xác nhận diện theo điều kiện ánh sáng.**
  * *AC1:* Cung cấp thanh trượt value từ `0.1` đến `0.9` (mặc định `0.5`).
  * *AC2:* Thay đổi có hiệu lực ngay lập tức lên luồng AI mà không cần khởi động lại app.
  * *AC3:* Hiển thị rõ giá trị $Conf$ hiện tại bên cạnh slider.

* **US-04: Tùy chỉnh chế độ hiển thị overlay**
  * *User Story:* Là một **Người vận hành**, tôi muốn **bật/tắt các lớp thông tin hiển thị (Bounding Box, Track ID, FPS, Vạch đếm)**, để **dễ dàng quan sát khung hình theo nhu cầu.**
  * *AC1:* Cung cấp các công tắc (Checkbox/Switch) độc lập cho: Bounding Box, Track ID, FPS, Vạch đếm.
  * *AC2:* Việc ẩn/hiện lớp thông tin không ảnh hưởng đến logic tính toán đếm xe bên dưới.

* **US-05: Theo dõi các chỉ số thống kê và cảnh báo Real-time**
  * *User Story:* Là một **Người vận hành**, tôi muốn **xem chỉ số đếm xe và nhận cảnh báo trực quan khi có xe vi phạm**, để **nắm bắt tình hình tức thì.**
  * *AC1:* Hiển thị bảng thông số real-time: Tổng số xe đã đếm, FPS hệ thống.
  * *AC2:* Khi xe đứng yên quá thời gian trong vùng ROI (>30s), ROI chuyển màu đỏ và phát thông báo "Cảnh báo đỗ xe trái phép!".

* **US-06: Trích xuất báo cáo dữ liệu**
  * *User Story:* Là một **Người vận hành**, tôi muốn **xuất dữ liệu thống kê đếm xe ra file Excel/CSV**, để **phục vụ mục đích báo cáo và lưu trữ.**
  * *AC1:* Cung cấp nút nhấn "Xuất báo cáo (Export Excel/CSV)".
  * *AC2:* File chứa các cột tối thiểu: `STT`, `Timestamp`, `Track ID`, `Hướng di chuyển`.
  * *AC3:* File được lưu thành công vào thư mục tùy chọn của người dùng.

* **US-15: Quản lý và tùy chỉnh khu vực cấm đỗ**
  * *User Story:* Là một **Người vận hành**, tôi muốn **vẽ các vùng cấm đỗ và thiết lập thời gian đứng yên tối đa**, để **hệ thống tự động phát hiện xe đỗ sai quy định.**
  * *AC1:* Cho phép vẽ vùng đa giác (Polygon ROI) đánh dấu vùng cấm đỗ.
  * *AC2:* Ô nhập liệu cài đặt thời gian ngưỡng (giây).
  * *AC3:* Lưu cấu hình vùng cấm đỗ vào file `config.json` để tái sử dụng.

* **US-16: Xem lại hình ảnh/video vi phạm**
  * *User Story:* Là một **Người vận hành**, tôi muốn **xem danh sách và mở lại các ảnh/clip bằng chứng vi phạm ngay trên giao diện**, để **kiểm tra và đối soát.**
  * *AC1:* Giao diện có tab danh sách hiển thị các sự kiện vi phạm (`Thời gian`, `Track ID`, `Loại vi phạm`).
  * *AC2:* Nhấp vào một dòng sự kiện sẽ hiển thị ảnh chụp (Snapshot) có khoanh vùng xe vi phạm.
  * *AC3:* Hỗ trợ nút "Xóa" hoặc "Xuất tệp" cho từng bằng chứng.

* **US-17: Cấu hình ghi video output**
  * *User Story:* Là một **Người vận hành**, tôi muốn **Bật/Tắt tính năng ghi hình luồng video đã xử lý**, để **lưu lại toàn bộ quá trình giám sát làm tài liệu truy xuất.**
  * *AC1:* Cung cấp nút Toggle "Ghi hình Video (Record Output)".
  * *AC2:* Chọn thư mục lưu trữ và định dạng video (`.mp4` / `.avi`).
  * *AC3:* Hiển thị biểu tượng nhấp nháy `REC` khi đang ghi hình.

* **US-18: Tùy chỉnh phương thức cảnh báo**
  * *User Story:* Là một **Người vận hành**, tôi muốn **tùy chỉnh bật/tắt chuông âm thanh và Pop-up cảnh báo**, để **không bị làm phiền khi không cần thiết.**
  * *AC1:* Cung cấp tùy chọn Bật/Tắt âm thanh cảnh báo.
  * *AC2:* Cung cấp tùy chọn Bật/Tắt thông báo Pop-up nổi.
  * *AC3:* Cung cấp nút "Thử âm thanh (Test Sound)".

* **US-19: Đặt lại bộ đếm (Reset Counter)**
  * *User Story:* Là một **Người vận hành**, tôi muốn **nhấn nút "Reset Counter" để đưa các số liệu đếm về 0**, để **bắt đầu một đợt đếm lưu lượng mới.**
  * *AC1:* Cung cấp nút nhấn "Reset Counter" rõ ràng.
  * *AC2:* Hiển thị hộp thoại xác nhận khi nhấn nút.
  * *AC3:* Khi xác nhận, số lượng xe đếm và danh sách Track ID xóa về 0 ngay lập tức.

---

### 2. Nhóm User Story cho Tác nhân: Bộ xử lý AI (AI Detection & Tracking Engine)

* **US-07: Tự động trích xuất và tiền xử lý khung hình**
  * *User Story:* Là một **Bộ xử lý AI**, tôi muốn **tự động nhận khung hình thô và chuẩn hóa kích thước/pixel**, để **chuẩn bị dữ liệu phù hợp cho mô hình YOLOv8.**
  * *AC1:* Tiếp nhận thành công khung hình thô BGR từ OpenCV.
  * *AC2:* Resize về $640 \times 640$ và chuẩn hóa pixel về $[0, 1]$ dưới $5\text{ ms}$/frame.

* **US-08: Phát hiện đối tượng xe hơi (Car Detection)**
  * *User Story:* Là một **Bộ xử lý AI**, tôi muốn **nhận diện vị trí và phân loại chính xác các xe hơi trong khung hình**, để **thu được tọa độ Bounding Box.**
  * *AC1:* Chỉ giữ lại các nhận diện thuộc lớp `car` / `vehicle`.
  * *AC2:* Loại bỏ các nhận diện có điểm tin cậy dưới ngưỡng $Conf$.
  * *AC3:* Trả về danh sách tọa độ $[x_1, y_1, x_2, y_2]$ và score.

* **US-09: Theo dõi đối tượng liên tục (Object Tracking)**
  * *User Story:* Là một **Bộ xử lý AI**, tôi muốn **gán và duy trì một Track ID duy nhất cho mỗi chiếc xe qua các khung hình**, để **tránh đếm trùng lặp.**
  * *AC1:* Dùng ByteTrack/DeepSORT liên kết đối tượng giữa Frame $N$ và Frame $N+1$.
  * *AC2:* Cấp Track ID tăng dần duy nhất cho xe mới.
  * *AC3:* Duy trì Track ID cũ nếu xe bị che khuất ngắn (<15 frames).

* **US-10: Tính toán logic đếm xe qua vạch**
  * *User Story:* Là một **Bộ xử lý AI**, tôi muốn **kiểm tra sự giao cắt giữa tâm xe với vạch ảo**, để **tăng số lượng đếm xe.**
  * *AC1:* Tính tọa độ tâm $C(x,y)$ của Bounding Box.
  * *AC2:* Khi vector tâm $C$ cắt vạch ảo, tăng bộ đếm $+1$.
  * *AC3:* Đảm bảo mỗi Track ID chỉ được đếm duy nhất 1 lần.

---

### 3. Nhóm User Story cho Tác nhân: Nguồn vào Video

* **US-11: Cung cấp luồng khung hình liên tục**
  * *User Story:* Là một **Nguồn vào Video**, tôi muốn **liên tục đọc và truyền khung hình thô đến AI Engine**, để **hệ thống vận hành real-time không bị gián đoạn.**
  * *AC1:* Đọc từng frame từ File/Camera đẩy vào Queue xử lý với độ trễ tối thiểu.
  * *AC2:* Tự động giải phóng frame cũ khỏi RAM để tránh leak memory.

* **US-12: Tự động phục hồi kết nối luồng RTSP**
  * *User Story:* Là một **Nguồn vào Video**, tôi muốn **tự động phát hiện mất kết nối mạng và thử kết nối lại**, để **hệ thống không bị sập đột ngột.**
  * *AC1:* Khi luồng RTSP bị ngắt, phát tín hiệu ngắt kết nối lên GUI thay vì crash app.
  * *AC2:* Thử kết nối lại (Re-try) sau mỗi $5\text{ giây}$.

---

### 4. Nhóm User Story cho Tác nhân: Hệ thống Lưu trữ & Báo cáo

* **US-13: Ghi nhận sự kiện thời gian thực**
  * *User Story:* Là một **Hệ thống Lưu trữ**, tôi muốn **tự động lưu thông tin sự kiện đếm/vi phạm vào database/log**, để **phục vụ truy vết và lập báo cáo.**
  * *AC1:* Khi đếm thành công, lưu `Timestamp`, `Track ID`, `Confidence` vào bộ nhớ tạm/SQLite.
  * *AC2:* Ghi log diễn ra trên luồng phụ (Background Thread) để không suy giảm FPS.

* **US-14: Chụp và lưu trữ hình ảnh vi phạm**
  * *User Story:* Là một **Hệ thống Lưu trữ**, tôi muốn **tự động chụp ảnh khung hình xe vi phạm và lưu vào thư mục**, để **làm bằng chứng.**
  * *AC1:* Khi có tín hiệu vi phạm, tự động cắt ảnh frame chứa đối tượng.
  * *AC2:* Tệp ảnh lưu với tên định dạng: `VIPHAM_[TrackID]_[YYYYMMDD_HHMMSS].jpg`.

---

## PHẦN 5: CHI TIẾT MÔ-ĐUN VÀ CHỨC NĂNG HỆ THỐNG

### 📦 MOD-01: MÔ-ĐUN GIAO DIỆN NGƯỜI DÙNG (GUI MODULE)
* **Mô tả chi tiết:** Nhận phản hồi từ người dùng (chuột, bàn phím) gửi lệnh điều khiển xuống các mô-đun bên dưới, đồng thời hiển thị luồng video realtime, chỉ số thống kê và cảnh báo.

#### Danh sách chức năng:
1. **FUNC-01.1: Quản lý Bảng điều khiển Nguồn vào (Input Controller Panel)**
   * *Mô tả:* Cung cấp giao diện chọn file video (`.mp4`), nhập URL RTSP hoặc chọn Webcam. Cung cấp nút `Play`, `Pause`, `Stop`.
2. **FUNC-01.2: Vẽ và Điều chỉnh Vùng/Vạch Ảo (Interactive Canvas Drawer)**
   * *Mô tả:* Dùng chuột kéo/vẽ vạch đếm xe (Virtual Line) hoặc vùng cấm đỗ (Polygon ROI) trên canvas.
3. **FUNC-01.3: Điều chỉnh Tham số Nhận diện (AI Parameter Tuning Controls)**
   * *Mô tả:* Cung cấp thanh trượt điều chỉnh ngưỡng $Conf$ và các công tắc ẩn/hiện Bounding Box, Track ID, FPS, Vạch đếm.
4. **FUNC-01.4: Hiển thị Chỉ số Real-time & Cảnh báo (Real-time Dashboard & Alerts Display)**
   * *Mô tả:* Bảng chỉ số cập nhật liên tục (Số xe đếm được, FPS). Nhấp nháy màu đỏ và phát âm thanh khi có xe vi phạm đỗ quá giờ.
5. **FUNC-01.5: Trình duyệt Xem Bằng chứng & Xuất Báo cáo (Evidence Viewer & Export UI)**
   * *Mô tả:* Bảng chứa danh sách sự kiện, xem ảnh chụp bằng chứng (Snapshot), nút trích xuất Excel/CSV và nút `Reset Counter`.

---

### 📦 MOD-02: MÔ-ĐUN XỬ LÝ LUỒNG DỮ LIỆU ĐẦU VÀO (VIDEO STREAMING MODULE)
* **Mô tả chi tiết:** Hoạt động trên luồng phụ (Background Thread) giao tiếp với Camera/File video để đọc, phân tách và đẩy khung hình (Frame) thô vào hàng đợi (Queue).

#### Danh sách chức năng:
1. **FUNC-02.1: Bộ đọc Luồng Video Đa nguồn (Multi-Source Frame Reader)**
   * *Mô tả:* Dùng OpenCV (`cv2.VideoCapture`) đọc file video, Webcam hoặc RTSP IP Camera.
2. **FUNC-02.2: Quản lý Hàng đợi & Giải phóng Bộ nhớ (Frame Queue & Memory Manager)**
   * *Mô tả:* Duy trì cấu trúc hàng đợi (FIFO Queue) chứa frame thô và giải phóng bộ nhớ RAM các frame cũ để tránh leak.
3. **FUNC-02.3: Tự động Kết nối lại Luồng Camera (RTSP Auto-Reconnector)**
   * *Mô tả:* Kiểm tra trạng thái mạng RTSP, tự động Retry kết nối lại sau mỗi $5\text{s}$ nếu đứt luồng.

---

### 📦 MOD-03: MÔ-ĐUN THỊ GIÁC MÁY TÍNH & AI CỐT LÕI (CORE AI & COMPUTER VISION MODULE)
* **Mô tả chi tiết:** Trái tim của hệ thống. Nhận frame thô, tiền xử lý, chạy YOLOv8 phát hiện xe hơi, chạy ByteTrack gán ID, và tính toán logic giao cắt vạch đếm/vùng cấm.

#### Danh sách chức năng:
1. **FUNC-03.1: Tiền xử lý Khung hình (Frame Pre-processor)**
   * *Mô tả:* Resize khung hình về $640 \times 640$ và chuẩn hóa dải pixel về $[0, 1]$.
2. **FUNC-03.2: Phát hiện Xe hơi (YOLOv8 Car Detector)**
   * *Mô tả:* Chạy YOLOv8 (`yolov8n.pt`/`yolov8s.pt`), lọc các bbox thuộc nhãn `car` có điểm $Conf$ vượt ngưỡng.
3. **FUNC-03.3: Theo dõi Đối tượng Liên tục (ByteTrack / DeepSORT Object Tracker)**
   * *Mô tả:* Liên kết các bbox giữa các khung hình liên tiếp để gán duy nhất 1 `Track ID` cho mỗi xe.
4. **FUNC-03.4: Phân tích Logic Cắt Vạch & Đếm Xe (Line Crossing & Counting Logic)**
   * *Mô tả:* Kiểm tra tọa độ tâm $C(x,y)$ xe cắt qua vạch ảo thì tăng số lượng đếm xe $+1$ (mỗi ID đếm 1 lần).
5. **FUNC-03.5: Phân tích Đỗ xe Trái phép trong Vùng Cấm (Parking Violation Analytics)**
   * *Mô tả:* Kiểm tra xe nằm trong vùng ROI cấm đỗ quá thời gian ngưỡng (ví dụ: $>30\text{s}$) thì kích hoạt báo động.
6. **FUNC-03.6: Tổng hợp & Vẽ Lớp Thông tin (Overlay Annotator)**
   * *Mô tả:* Vẽ Bounding Box, Track ID, vạch đếm, vùng ROI và thông số lên frame trước khi đưa lên GUI.

---

### 📦 MOD-04: MÔ-ĐUN LƯU TRỮ VÀ XUẤT BÁO CÁO (STORAGE & REPORTING MODULE)
* **Mô tả chi tiết:** Quản lý dữ liệu đầu ra: lưu vết nhật ký sự kiện, quản lý ảnh/video bằng chứng vi phạm, và đóng gói xuất file báo cáo.

#### Danh sách chức năng:
1. **FUNC-04.1: Ghi nhật ký Sự kiện (Real-time Event Logger)**
   * *Mô tả:* Ghi nhận thông tin mỗi khi có xe đếm được hoặc vi phạm (`Timestamp`, `Track ID`, `Event Type`) vào database.
2. **FUNC-04.2: Lưu trữ Bằng chứng Vi phạm (Violation Snapshot & Clip Capture)**
   * *Mô tả:* Tự động crop khoanh vùng xe vi phạm và lưu thành tệp ảnh `.jpg` vào ổ đĩa.
3. **FUNC-04.3: Ghi hình Luồng Video Output (Video Recorder Engine)**
   * *Mô tả:* Dùng `cv2.VideoWriter` đóng gói toàn bộ luồng video đã vẽ overlay thành tệp `.mp4` / `.avi`.
4. **FUNC-04.4: Trích xuất Báo cáo Dữ liệu (Excel / CSV Report Exporter)**
   * *Mô tả:* Đóng gói nhật ký sự kiện thành tệp báo cáo định dạng Excel (`.xlsx`) hoặc CSV.

---

## PHẦN 6: MA TRẬN MÔ-ĐUN & CHỨC NĂNG

| Mã Mô-đun | Tên Mô-đun | Danh sách Mã Chức năng | Số lượng Chức năng |
| :--- | :--- | :--- | :---: |
| **MOD-01** | Giao diện Người dùng (GUI) | FUNC-01.1 $\rightarrow$ FUNC-01.5 | 05 |
| **MOD-02** | Xử lý Luồng Input (Streaming) | FUNC-02.1 $\rightarrow$ FUNC-02.3 | 03 |
| **MOD-03** | AI & CV Cốt lõi (Core AI) | FUNC-03.1 $\rightarrow$ FUNC-03.6 | 06 |
| **MOD-04** | Lưu trữ & Báo cáo (Storage) | FUNC-04.1 $\rightarrow$ FUNC-04.4 | 04 |
| **TỔNG CỘNG** | **04 Mô-đun** | **FUNC-01.1 $\rightarrow$ FUNC-04.4** | **18 Chức năng** |
# Hướng dẫn sử dụng AutoGuardian

AutoGuardian là phần mềm giám sát giao thông bằng camera trên máy tính Windows. Phần mềm tự động:

- **Nhận diện và bám theo từng xe** (ô tô, xe máy, xe buýt, xe tải).
- **Đếm xe** đi qua một vạch ảo, phân biệt chiều vào / chiều ra.
- **Đo tốc độ** xe giữa hai mốc trên đường.
- **Đọc biển số xe** và hiển thị kèm ảnh chụp biển số.
- **Cảnh báo đỗ xe trái phép** trong vùng cấm, tự chụp ảnh bằng chứng.
- **Ghi hình và xuất báo cáo** Excel / CSV.

---

## Mục lục

1. [Yêu cầu máy tính](#1-yêu-cầu-máy-tính)
2. [Cài đặt](#2-cài-đặt)
3. [Bắt đầu nhanh trong 5 bước](#3-bắt-đầu-nhanh-trong-5-bước)
4. [Giao diện chính](#4-giao-diện-chính)
5. [Hướng dẫn từng chức năng](#5-hướng-dẫn-từng-chức-năng)
6. [Dữ liệu và cấu hình](#6-dữ-liệu-và-cấu-hình)
7. [Xử lý sự cố thường gặp](#7-xử-lý-sự-cố-thường-gặp)

---

## 1. Yêu cầu máy tính

| | Tối thiểu | Khuyên dùng |
|---|---|---|
| Hệ điều hành | Windows 10 64-bit | Windows 11 64-bit |
| CPU | 4 nhân | 8 nhân trở lên |
| RAM | 8 GB | 16 GB |
| Ổ đĩa trống | 2 GB (bản CPU) | 10 GB khi cài, 4.2 GB sau cài (bản GPU) |
| Card đồ họa | Không bắt buộc | GPU NVIDIA (GTX 10xx trở lên) với driver mới |
| Internet | Cần cho lần cài đặt đầu tiên | |

> Không có card NVIDIA vẫn dùng được (chạy bằng CPU), chỉ là xử lý chậm hơn.
> Card AMD / Intel hiện chạy bằng CPU.

---

## 2. Cài đặt

### Cách 1 – Dùng bộ cài đặt (khuyên dùng)

1. Vào trang **Releases** của dự án:
   <https://github.com/NguyenMinhPhuc/pro-dem-va-tinh-van-toc/releases/latest>
2. Tải file **`AutoGuardian-Setup.exe`** (khoảng 10 MB).
3. Mở file vừa tải.
   - Nếu Windows hiện cảnh báo *"Windows protected your PC"*: bấm **More info** → **Run anyway**.
     (Cảnh báo này xuất hiện vì phần mềm chưa được ký số, không phải do có virus.)
4. Bộ cài tự kiểm tra máy và gợi ý bản phù hợp:

   ![Bộ cài đặt AutoGuardian](docs/images/bo-cai-dat.png)

   - **GPU NVIDIA (CUDA) + CPU** – tải khoảng 2.5 GB. Chọn khi máy có card NVIDIA: xử lý nhanh hơn nhiều.
     Bản này vẫn tự chạy bằng CPU nếu sau này máy không có GPU.
   - **Chỉ CPU (nhẹ)** – tải khoảng 343 MB. Chọn khi máy không có card NVIDIA hoặc mạng chậm.
5. Bấm **Cài đặt** và chờ tải xong. Nếu mất mạng hoặc lỡ đóng cửa sổ, chỉ cần mở lại bộ cài:
   phần mềm **tải tiếp từ chỗ đang dừng**, không phải tải lại từ đầu.
6. Cài xong, AutoGuardian tự mở. Trên Desktop và Start Menu có thêm biểu tượng **AutoGuardian**.

Những lần sau chỉ cần mở biểu tượng **AutoGuardian**. Nếu có phiên bản mới, phần mềm sẽ hỏi bạn có muốn
cập nhật không. **Khi cập nhật, cấu hình (vạch đếm, vùng cấm, mốc tốc độ…) và dữ liệu (ảnh vi phạm, báo cáo)
được giữ nguyên.**

Phần mềm được cài vào thư mục `%LOCALAPPDATA%\AutoGuardian` (thường là
`C:\Users\<tên bạn>\AppData\Local\AutoGuardian`), không cần quyền Administrator.

### Cách 2 – Tải gói nén thủ công (không cần bộ cài)

Dùng khi máy cần cài không có Internet: tải gói trên một máy khác rồi chép sang.

1. Vào release **v1.1.0** (*Gói dữ liệu cho bộ cài*) trên trang Releases.
2. Tải một trong hai:
   - Bản CPU: `AutoGuardian-win64.zip`
   - Bản GPU: **cả hai file** `AutoGuardian-win64-cuda.zip.001` và `AutoGuardian-win64-cuda.zip.002` (để cùng một thư mục).
3. Giải nén:
   - Bản CPU: chuột phải → *Extract All*.
   - Bản GPU: dùng [7-Zip](https://www.7-zip.org/), chuột phải file `.001` → *7-Zip* → *Extract Here*.
     Hoặc mở *Command Prompt* tại thư mục đó và chạy:
     `copy /b AutoGuardian-win64-cuda.zip.001+AutoGuardian-win64-cuda.zip.002 AutoGuardian-win64-cuda.zip`
     rồi giải nén file `.zip` như bình thường.
4. Mở `AutoGuardian\AutoGuardian.exe`.

### Gỡ cài đặt

1. Đóng AutoGuardian.
2. Xóa thư mục `%LOCALAPPDATA%\AutoGuardian` (dán đường dẫn này vào thanh địa chỉ của File Explorer).
   *Lưu ý: thao tác này xóa cả ảnh vi phạm và báo cáo trong `outputs\` – hãy sao lưu trước nếu cần.*
3. Xóa biểu tượng AutoGuardian trên Desktop và trong Start Menu.

---

## 3. Bắt đầu nhanh trong 5 bước

1. **Chọn nguồn video:** bấm **📁 Chọn Video** và chọn file `.mp4` (hoặc mở Webcam / camera IP).
   Video bắt đầu chạy ngay, xe được khoanh khung và đánh số.
2. **Vẽ vạch đếm:** bấm **✏️ Vẽ Vạch Đếm**, kéo chuột cắt ngang làn đường.
3. **Đặt mốc đo tốc độ:** chọn làn, bấm **🚩 Vẽ Mốc A**, **🏁 Vẽ Mốc B**, rồi **📏 Khoảng Cách** để nhập
   khoảng cách thật (mét) giữa hai mốc.
4. **(Tùy chọn) Vẽ vùng cấm đỗ:** bấm **📐 Vẽ Vùng Cấm Đỗ**, nhấp các đỉnh, nhấp chuột phải để kết thúc.
5. **Theo dõi kết quả** ở bảng bên phải; cuối buổi bấm **📊 Xuất Excel** để lưu báo cáo.

---

## 4. Giao diện chính

![Giao diện chính AutoGuardian](docs/images/giao-dien-chinh.jpg)

| Khu vực | Vị trí | Chức năng |
|---|---|---|
| **Thanh công cụ vẽ** | Trên cùng bên trái | Vẽ vạch đếm, vùng cấm đỗ, mốc đo tốc độ |
| **Khung video** | Giữa bên trái | Hình ảnh trực tiếp kèm khung xe, mã xe, tốc độ, biển số |
| **Thanh điều khiển** | Dưới khung video | Bắt đầu / tạm dừng / dừng, ghi hình, reset, xuất báo cáo |
| **Nguồn dữ liệu video** | Trên cùng bên phải | Chọn file video, webcam, camera IP |
| **Tham số AI & hiển thị** | Bên phải | Độ nhạy nhận diện, hiệu chỉnh tốc độ, ẩn/hiện các lớp vẽ |
| **Dashboard** | Giữa bên phải | Các con số thống kê theo thời gian thực, trạng thái cảnh báo |
| **Bảng biển số / vi phạm** | Dưới cùng bên phải | Danh sách biển số đã đọc và các vụ đỗ xe sai |
| **Thanh trạng thái** | Đáy cửa sổ | Thông báo hiện tại (nguồn đang phát, thao tác vừa làm…) |

Trên mỗi xe trong video hiển thị: `#mã xe | loại xe | [biển số] | tốc độ km/h | độ tin cậy`.

---

## 5. Hướng dẫn từng chức năng

### 5.1. Nguồn video

| Nguồn | Cách dùng |
|---|---|
| **File video** | Bấm **📁 Chọn Video (.mp4 / .avi)** và chọn file (`.mp4`, `.avi`, `.mkv`, `.mov`). |
| **Webcam** | Chọn *Webcam 0 / 1 / 2* trong danh sách rồi bấm **📹 Mở Webcam**. |
| **Camera IP** | Bấm **🌐 Kết nối Camera IP (RTSP)**, nhập địa chỉ, ví dụ `rtsp://admin:matkhau@192.168.1.100:554/stream1`. Nếu mất mạng, phần mềm tự kết nối lại sau mỗi 5 giây. |

- Ô **🔁 Lặp lại video MP4 liên tục**: khi hết video sẽ tự phát lại từ đầu (bỏ chọn nếu muốn dừng ở cuối video).
- **▶ Bắt đầu / ⏸ Tạm dừng / ⏹ Dừng luồng**: điều khiển việc phát và xử lý.

### 5.2. Đếm xe qua vạch

1. Bấm **✏️ Vẽ Vạch Đếm** (chữ "Chế độ" ở góc trái đổi màu để báo đang vẽ).
2. Nhấn giữ chuột trái tại điểm đầu, kéo tới điểm cuối, thả chuột. Vạch màu vàng xuất hiện ngay.
3. Mỗi xe chỉ được đếm **một lần** khi cắt qua vạch; hướng đi quyết định xe được tính vào
   **Chiều Vào (IN)** hay **Chiều Ra (OUT)**.

Mẹo: vẽ vạch cắt ngang toàn bộ các làn, ở đoạn xe đi thẳng và không bị che khuất.
Bấm **✖ Hủy Vẽ** nếu muốn thôi vẽ.

### 5.3. Đo tốc độ

Phần mềm đo tốc độ chính xác nhất bằng **hai mốc**: thời gian xe đi từ Mốc A tới Mốc B và khoảng cách
thật giữa hai mốc. Mỗi chiều đường (Làn Vào / Làn Ra) có cặp mốc riêng.

1. Chọn làn trong danh sách **🚗 Làn Vào (IN)** / **🚙 Làn Ra (OUT)**.
2. Bấm **🚩 Vẽ Mốc A** và kéo chuột vẽ vạch ngang làn tại điểm xe đi vào.
3. Bấm **🏁 Vẽ Mốc B** và kéo chuột vẽ vạch tại điểm xe đi ra.
4. Bấm **📏 Khoảng Cách** và nhập **khoảng cách thực tế giữa hai mốc (mét)**. Đây là yếu tố quyết định độ chính xác:
   hãy đo ngoài thực địa, hoặc đặt hai mốc tại những vật có khoảng cách biết trước (vạch kẻ đường, cột mốc, cột đèn).
5. Lặp lại cho làn còn lại. Bấm **↺ Mặc Định** để trả các mốc về vị trí ban đầu.

Với xe chưa đi qua đủ hai mốc, phần mềm ước lượng tốc độ tạm thời theo **Tỷ lệ Pixel/Mét**
(khung *Tham số AI*). Có sẵn các mức gợi ý: *Cao tốc 1080p (22 px/m)*, *Đô thị 1080p (35 px/m)*,
*720p (12 px/m)*. Kết quả theo hai mốc luôn được ưu tiên vì chính xác hơn.

### 5.4. Nhận diện biển số

Phần mềm tự đọc biển số, không cần thao tác. Cách hoạt động:

- Mỗi xe được đọc **nhiều lần** khi tiến lại gần camera; phần mềm so sánh các lần đọc và chỉ hiển thị
  kết quả khi đủ tin cậy (mặc định ≥ 90%). Vì vậy biển số thường xuất hiện **sau vài giây**.
- Hỗ trợ biển số của 65 quốc gia/khu vực, gồm **Việt Nam**, Anh, các nước EU, Mỹ…
- Kết quả hiện ở tab **📋 Biển Số Real-time**: ảnh biển số, chuỗi biển số, mã xe, vận tốc, thời gian.
  Cột *Vận Tốc* hiện "Đang đo..." cho tới khi xe đi qua đủ hai mốc.
- **Khi ảnh quá nhỏ hoặc mờ, phần mềm bỏ qua thay vì đoán** – nên có xe sẽ không có biển số.

Để đọc biển số tốt:

| Nên | Tránh |
|---|---|
| Camera độ phân giải ≥ 1080p, hướng chéo vừa phải vào đầu/đuôi xe | Camera đặt quá cao, quá xa |
| Biển số rộng tối thiểu ~40–50 điểm ảnh trên khung hình | Video bị nén mạnh, nhòe chuyển động |
| Đủ sáng, không bị chói đèn pha | Ngược sáng, ban đêm không có đèn chiếu |

### 5.5. Cảnh báo đỗ xe trái phép

1. Bấm **📐 Vẽ Vùng Cấm Đỗ**.
2. Nhấp chuột trái lần lượt tại các đỉnh của vùng (ít nhất 3 đỉnh).
3. **Nhấp chuột phải** hoặc **nhấp đúp** để khép vùng. Vùng màu xanh lá xuất hiện.
4. Bấm **⚙️ Cài Ngưỡng Đỗ** để đặt:
   - **Thời gian đỗ tối đa** (mặc định 30 giây).
   - **Sai số đứng yên** (mặc định 20 điểm ảnh) – xe xê dịch ít hơn mức này vẫn coi là đang đỗ.

Khi một xe đứng yên trong vùng lâu hơn ngưỡng: vùng chuyển **màu đỏ**, thanh trạng thái báo vi phạm,
chuông kêu (nếu bật **Chuông âm thanh**), cửa sổ cảnh báo bật lên (nếu bật **Popup cảnh báo**), và ảnh
bằng chứng được chụp tự động. Bấm **🔔 Thử Âm Thanh** để kiểm tra loa.

### 5.6. Dashboard

| Thẻ | Ý nghĩa |
|---|---|
| **Tổng Xe Đếm** | Số xe đã đi qua vạch đếm |
| **Chiều Vào (IN) / Chiều Ra (OUT)** | Số xe theo từng hướng |
| **Vi Phạm Đỗ Xe** | Số lượt vi phạm đã ghi nhận |
| **Tốc Độ FPS** | Số khung hình xử lý mỗi giây (càng cao càng mượt) |
| **Xe Trong Vùng Cấm** | Số xe đang nằm trong vùng cấm đỗ |

### 5.7. Xem ảnh bằng chứng vi phạm

Mở tab **🚨 Vi Phạm Đỗ Xe** và **nhấp đúp** vào một dòng để xem ảnh phóng to (xe vi phạm được khoanh đỏ,
kèm thời gian và mã xe). Ảnh được lưu trong `outputs\captures\` với tên dạng
`VIPHAM_<mã xe>_<ngày>_<giờ>.jpg`.

### 5.8. Ghi hình, đặt lại, xuất báo cáo

- **⏺ Ghi hình (REC)**: ghi lại video đang xử lý (kèm khung xe, vạch, tốc độ). Bấm lần nữa để dừng.
  Video lưu trong `outputs\recordings\`. Cần đang phát video thì mới ghi được.
- **🔄 Reset Counter**: xóa toàn bộ số liệu đếm và danh sách vi phạm (có hỏi xác nhận).
- **📊 Xuất Excel**: xuất báo cáo gồm 2 trang tính *Lưu lượng xe đếm* và *Sự kiện vi phạm* (kèm biển số, tốc độ).
- **📄 Xuất CSV**: xuất dữ liệu lưu lượng dạng CSV, mở được bằng Excel không lỗi tiếng Việt.

Báo cáo mặc định lưu trong `outputs\reports\` (có thể chọn nơi lưu khác khi xuất).

### 5.9. Tinh chỉnh hiển thị

- **Ngưỡng tin cậy (Conf)**: kéo sang phải để chỉ giữ các xe được nhận diện chắc chắn (ít nhận nhầm hơn
  nhưng dễ sót xe); kéo sang trái để bắt được nhiều xe hơn. Mặc định 0.50.
- Các ô **Bounding Box**, **Track ID**, **Hiển thị FPS**, **Vạch Đếm Ảo**, **Vùng Cấm Đỗ (ROI)**,
  **Speed Trap (2 Mốc)** dùng để ẩn/hiện từng lớp vẽ trên video (không ảnh hưởng việc đếm).

---

## 6. Dữ liệu và cấu hình

Mọi thứ nằm trong thư mục cài đặt (`%LOCALAPPDATA%\AutoGuardian\AutoGuardian\` nếu dùng bộ cài):

| Thư mục / file | Nội dung |
|---|---|
| `outputs\captures\` | Ảnh bằng chứng vi phạm |
| `outputs\recordings\` | Video đã ghi |
| `outputs\reports\` | Báo cáo Excel / CSV |
| `outputs\autoguardian.db` | Cơ sở dữ liệu sự kiện (lưu lượng, vi phạm) |
| `outputs\logs\autoguardian.log` | Nhật ký lỗi của phần mềm |
| `configs\zones.json` | Vạch đếm, vùng cấm đỗ, mốc tốc độ (tự lưu khi bạn vẽ) |
| `configs\config.json` | Cấu hình nâng cao |

Một số tùy chọn trong `configs\config.json` (sửa bằng Notepad khi phần mềm đang **đóng**):

| Tùy chọn | Ý nghĩa | Mặc định |
|---|---|---|
| `ai.device` | `"auto"` (tự dùng GPU nếu có), `"cpu"` (luôn dùng CPU), `"cuda"` | `"auto"` |
| `plate_recognition.enabled` | Bật/tắt đọc biển số (`true` / `false`). Tắt để tăng FPS trên máy yếu | `true` |
| `plate_recognition.min_confidence` | Độ tin cậy tối thiểu để hiển thị biển số (0–1). Tăng để ít sai hơn, giảm để đọc được nhiều hơn | `0.9` |
| `plate_recognition.max_reads_per_frame` | Số lần đọc biển số tối đa mỗi khung hình. Giảm xuống `1` nếu máy chậm | `2` |
| `plate_recognition.min_bbox_width` | Chỉ đọc biển số khi khung xe rộng hơn số điểm ảnh này | `90` |

---

## 7. Xử lý sự cố thường gặp

**Windows báo "Windows protected your PC" khi mở bộ cài**
Bấm **More info** → **Run anyway**. Phần mềm chưa được ký số nên Windows cảnh báo.

**Bộ cài báo "Không tải được thông tin phiên bản"**
Lần cài đầu cần Internet. Kiểm tra mạng, tường lửa hoặc proxy (cần truy cập được `github.com`).
Nếu mạng cơ quan chặn GitHub, dùng [Cách 2](#cách-2--tải-gói-nén-thủ-công-không-cần-bộ-cài).

**Bộ cài báo "Không đủ dung lượng ổ đĩa"**
Giải phóng ổ C (bản GPU cần khoảng 10 GB trống trong lúc cài, sau cài chiếm khoảng 4.2 GB) hoặc chọn bản CPU.

**Cập nhật báo "AutoGuardian đang mở"**
Đóng hẳn phần mềm (kiểm tra trong Task Manager không còn `AutoGuardian.exe`) rồi mở lại biểu tượng AutoGuardian.

**Máy có card NVIDIA nhưng không chạy bằng GPU (FPS thấp)**
- Kiểm tra đã cài **bản GPU** (cài lại bằng bộ cài và chọn bản GPU nếu cần).
- Cập nhật driver NVIDIA (cần bản 527.41 trở lên) tại <https://www.nvidia.com/Download/index.aspx>.
- Xem dòng `Using device:` trong `outputs\logs\autoguardian.log`: `cuda:0` là đang dùng GPU, `cpu` là CPU.

**Video chạy chậm / giật trên máy không có GPU**
Dùng video độ phân giải 720p, tắt đọc biển số hoặc đặt `max_reads_per_frame` = `1` (xem mục 6).

**Không đọc được biển số nào**
Thường do biển số trong video quá nhỏ (xem mẹo ở mục 5.4). Thử video quay gần hơn hoặc độ phân giải cao hơn.
Nếu file log có dòng `Plate recognition disabled`, hãy cài lại phần mềm.

**Tốc độ đo được không hợp lý**
Kiểm tra lại **📏 Khoảng Cách** giữa hai mốc (phải là khoảng cách thật, tính bằng mét) và vị trí hai mốc
có nằm đúng trên làn xe chạy không.

**Phần mềm không mở được hoặc tự tắt**
Mở file `outputs\logs\autoguardian.log` (và `%LOCALAPPDATA%\AutoGuardian\launcher.log` nếu lỗi khi cài)
để xem thông báo lỗi, rồi gửi kèm khi báo lỗi.

**Báo lỗi / góp ý**
Tạo *Issue* tại <https://github.com/NguyenMinhPhuc/pro-dem-va-tinh-van-toc/issues>, đính kèm mô tả,
ảnh chụp màn hình và file log.

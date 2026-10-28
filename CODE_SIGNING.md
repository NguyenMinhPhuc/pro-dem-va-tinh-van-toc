# Code signing policy

Free code signing provided by [SignPath.io](https://about.signpath.io/), certificate by [SignPath Foundation](https://signpath.org/).

*(Tiếng Việt: Chữ ký số miễn phí do SignPath.io cung cấp, chứng chỉ của SignPath Foundation. Tóm tắt chính sách ở cuối trang.)*

## Signed files

Only binaries built from this repository's source code by the
[release workflow](.github/workflows/release.yml) on GitHub Actions are signed:

| File | Description |
|---|---|
| `AutoGuardian-Setup.exe` | Lightweight installer / launcher (`launcher/autoguardian_launcher.py`) |
| `AutoGuardian.exe` | Application executable inside the CPU and GPU (CUDA) packages (`app.py`) |

Every signed binary carries the product name `AutoGuardian` and the release version. Third-party
components shipped in the packages (Python runtime, PyTorch, Qt, OpenCV, ONNX Runtime, NVIDIA CUDA
libraries, …) are included unmodified with their original upstream signatures, or unsigned, and are not
signed by this project.

## Team roles

| Role | Members |
|---|---|
| Authors (committers) | [@NguyenMinhPhuc](https://github.com/NguyenMinhPhuc), [@longho-lhu](https://github.com/longho-lhu) |
| Reviewers | [@NguyenMinhPhuc](https://github.com/NguyenMinhPhuc), [@longho-lhu](https://github.com/longho-lhu) |
| Approvers | [@NguyenMinhPhuc](https://github.com/NguyenMinhPhuc) (repository owner) |

- Changes from people outside the authors list are reviewed by a reviewer before merging.
- Every release signing request is manually approved in SignPath by an approver.
- All team members use multi-factor authentication for GitHub and SignPath.

## Privacy policy

**AutoGuardian (the application)** does not transfer any information to other networked systems unless
specifically requested by the user or the person installing or operating it. The only network connections
it makes are to video sources the operator configures (e.g. an RTSP IP camera URL). Usage analytics of the
bundled Ultralytics library are disabled (`YOLO_OFFLINE=1`). All results (counts, plates, snapshots,
recordings, reports) stay on the local computer.

**AutoGuardian-Setup.exe (the installer)** connects to `github.com` (GitHub Releases of this repository) to:

1. download `manifest.json` and the application package during installation, and
2. check for a newer version each time AutoGuardian is opened through its shortcut.

No personal data is sent; GitHub receives the usual information of an HTTP download request (IP address,
user agent) under the [GitHub Privacy Statement](https://docs.github.com/site-policy/privacy-policies/github-general-privacy-statement).
The update check can be disabled:

- untick *"Tự kiểm tra bản cập nhật mỗi khi mở"* on the installer screen, or
- run the installer with `--no-update-check`, or
- set `"check_updates": false` in `%LOCALAPPDATA%\AutoGuardian\installed.json`.

The installer creates Desktop and Start Menu shortcuts (skip with `--no-shortcuts`) and installs into
`%LOCALAPPDATA%\AutoGuardian` without administrator rights. Uninstall instructions:
[HUONG_DAN_SU_DUNG.md – Gỡ cài đặt](HUONG_DAN_SU_DUNG.md#gỡ-cài-đặt).

---

### Tóm tắt (tiếng Việt)

- Các file `AutoGuardian-Setup.exe` và `AutoGuardian.exe` được ký số miễn phí bởi SignPath Foundation; chúng chỉ
  được build tự động trên GitHub Actions từ mã nguồn công khai của repo này, và mỗi bản phát hành đều được
  người phê duyệt xác nhận thủ công.
- **Ứng dụng không gửi dữ liệu ra ngoài**, ngoài việc kết nối tới camera/nguồn video do bạn cấu hình.
- **Bộ cài** chỉ kết nối `github.com` để tải phần mềm và kiểm tra cập nhật – có thể tắt ngay trên màn hình cài đặt.

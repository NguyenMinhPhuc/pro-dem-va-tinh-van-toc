"""AutoGuardian Launcher - bộ cài đặt / khởi chạy nhẹ (vài MB).

Lần chạy đầu: phát hiện GPU NVIDIA, tải gói ứng dụng phù hợp (GPU hoặc CPU) từ GitHub Release,
tải tiếp được khi đứt mạng, kiểm tra SHA-256, giải nén vào %LOCALAPPDATA%\\AutoGuardian
và tạo shortcut. Các lần sau: kiểm tra bản cập nhật (nếu có mạng) rồi mở ứng dụng.

Chỉ dùng thư viện chuẩn của Python (tkinter, urllib, zipfile, hashlib).

Tham số dòng lệnh:
    --variant cpu|cuda   Bỏ qua màn hình chọn bản
    --reinstall          Cài lại (vẫn giữ configs/ và outputs/)
    --no-launch          Cài xong không mở ứng dụng
    --no-shortcuts       Không tạo shortcut Desktop / Start Menu
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import queue
import shutil
import subprocess
import sys
import threading
import traceback
import tkinter as tk
import urllib.error
import urllib.request
import zipfile
from datetime import datetime
from pathlib import Path
from tkinter import messagebox, ttk
from typing import Callable, Optional

REPO = "NguyenMinhPhuc/pro-dem-va-tinh-van-toc"
MANIFEST_URL = os.environ.get(
    "AUTOGUARDIAN_MANIFEST_URL", f"https://github.com/{REPO}/releases/latest/download/manifest.json"
)
INSTALL_ROOT = Path(os.environ.get("AUTOGUARDIAN_HOME") or Path(os.environ.get("LOCALAPPDATA", Path.home())) / "AutoGuardian")
APP_DIR = INSTALL_ROOT / "AutoGuardian"
APP_EXE = APP_DIR / "AutoGuardian.exe"
STATE_FILE = INSTALL_ROOT / "installed.json"
DOWNLOAD_DIR = INSTALL_ROOT / "downloads"
LAUNCHER_COPY = INSTALL_ROOT / "AutoGuardian-Launcher.exe"
LOG_FILE = INSTALL_ROOT / "launcher.log"
USER_DATA_DIRS = ("configs", "outputs")  # giữ nguyên khi cập nhật
MIN_CUDA12_DRIVER = (527, 41)  # driver Windows tối thiểu cho CUDA 12.x
CREATE_NO_WINDOW = 0x08000000
USER_AGENT = "AutoGuardian-Launcher/1.0"
CHUNK = 1024 * 1024


class CancelledError(Exception):
    """Người dùng bấm Hủy trong lúc tải."""


# ---------------------------------------------------------------------------
# Tiện ích
# ---------------------------------------------------------------------------
def parse_version(v: str) -> tuple[int, ...]:
    return tuple(int(p) for p in v.lstrip("v").split(".") if p.isdigit())


def log_error(exc: BaseException) -> None:
    """Ghi traceback vào launcher.log để hỗ trợ người dùng khi cài đặt lỗi."""
    try:
        INSTALL_ROOT.mkdir(parents=True, exist_ok=True)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"\n[{datetime.now():%Y-%m-%d %H:%M:%S}] {exc!r}\n")
            f.write("".join(traceback.format_exception(exc)))
    except OSError:
        pass


def longpath(path: Path) -> str:
    """Đường dẫn dạng \\\\?\\ để vượt giới hạn 260 ký tự của Windows (thư viện PyTorch có đường dẫn rất sâu)."""
    p = os.path.abspath(path)
    return "\\\\?\\" + p if os.name == "nt" and not p.startswith("\\\\?\\") else p


def human_mb(n_bytes: float) -> str:
    mb = n_bytes / 1024**2
    return f"{mb / 1024:.2f} GB" if mb >= 1024 else f"{mb:.0f} MB"


def detect_nvidia_gpu() -> Optional[dict]:
    """Trả về {'name', 'driver', 'cuda_ok'} nếu có GPU NVIDIA (qua nvidia-smi đi kèm driver)."""
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,driver_version", "--format=csv,noheader"],
            capture_output=True, text=True, timeout=10, creationflags=CREATE_NO_WINDOW,
        )
        line = out.stdout.strip().splitlines()[0]
        name, driver = [s.strip() for s in line.split(",", 1)]
        return {"name": name, "driver": driver, "cuda_ok": parse_version(driver) >= MIN_CUDA12_DRIVER}
    except Exception:
        return None


def fetch_manifest(timeout: float = 10.0) -> Optional[dict]:
    try:
        req = urllib.request.Request(MANIFEST_URL, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None


def load_state() -> Optional[dict]:
    try:
        state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        return state if APP_EXE.exists() else None
    except Exception:
        return None


def sha256_of(path: Path, progress: Callable[[int], None]) -> str:
    h = hashlib.sha256()
    done = 0
    with open(path, "rb") as f:
        while block := f.read(CHUNK * 4):
            h.update(block)
            done += len(block)
            progress(done)
    return h.hexdigest()


# ---------------------------------------------------------------------------
# Cài đặt (chạy trong luồng nền, báo tiến độ qua callback)
# ---------------------------------------------------------------------------
class Installer:
    def __init__(
        self, manifest: dict, variant: str, report: Callable[[str, float, str], None], shortcuts: bool = True
    ) -> None:
        self.manifest = manifest
        self.shortcuts = shortcuts
        self.variant = variant
        self.spec = manifest["variants"][variant]
        self.report = report  # (tiêu đề, phần trăm 0..100, chi tiết)
        self.cancel_event = threading.Event()

    def run(self) -> None:
        INSTALL_ROOT.mkdir(parents=True, exist_ok=True)
        DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
        self._check_disk_space()
        files = self.spec["files"]
        parts = [self._download(f, i, len(files)) for i, f in enumerate(files, 1)]
        archive = self._join_parts(parts)
        staging = self._extract(archive)
        self._swap_into_place(staging)
        shutil.rmtree(DOWNLOAD_DIR, ignore_errors=True)
        STATE_FILE.write_text(
            json.dumps({"version": self.manifest["app_version"], "variant": self.variant}, indent=2),
            encoding="utf-8",
        )
        if self.shortcuts:
            self._create_shortcuts()

    def _check_disk_space(self) -> None:
        download = sum(f["size"] for f in self.spec["files"])
        # tải về + file ghép (nếu nhiều phần) + giải nén
        needed = download * (2 if len(self.spec["files"]) > 1 else 1) + self.spec["unpacked_size"]
        free = shutil.disk_usage(INSTALL_ROOT).free
        if free < needed:
            raise RuntimeError(
                f"Không đủ dung lượng ổ đĩa: cần khoảng {human_mb(needed)}, còn trống {human_mb(free)}."
            )

    def _download(self, file: dict, index: int, total: int) -> Path:
        dest = DOWNLOAD_DIR / file["name"]
        part = dest.with_name(dest.name + ".part")
        title = f"Đang tải phần {index}/{total}: {file['name']}"

        if dest.exists() and dest.stat().st_size == file["size"]:
            if self._verify(dest, file, index, total):
                return dest
            dest.unlink()

        for attempt in range(1, 6):
            try:
                self._download_once(file, part, title)
                break
            except CancelledError:
                raise
            except (urllib.error.URLError, OSError, TimeoutError) as e:
                if attempt == 5:
                    raise RuntimeError(f"Tải thất bại sau 5 lần thử: {e}") from e
                self.report(title, -1, f"Mất kết nối, thử lại ({attempt}/5)...")
                self.cancel_event.wait(3 * attempt)

        part.replace(dest)
        if not self._verify(dest, file, index, total):
            dest.unlink()
            raise RuntimeError(f"File {file['name']} bị hỏng (sai SHA-256). Hãy chạy lại để tải lại.")
        return dest

    def _download_once(self, file: dict, part: Path, title: str) -> None:
        have = part.stat().st_size if part.exists() else 0
        if have >= file["size"]:
            return
        headers = {"User-Agent": USER_AGENT}
        if have:
            headers["Range"] = f"bytes={have}-"
        req = urllib.request.Request(file["url"], headers=headers)
        with urllib.request.urlopen(req, timeout=30) as resp:
            if have and resp.status != 206:  # máy chủ không hỗ trợ tải tiếp -> tải lại từ đầu
                have = 0
            with open(part, "ab" if have else "wb") as out:
                while True:
                    if self.cancel_event.is_set():
                        raise CancelledError()
                    block = resp.read(CHUNK)
                    if not block:
                        break
                    out.write(block)
                    have += len(block)
                    self.report(title, have * 100 / file["size"], f"{human_mb(have)} / {human_mb(file['size'])}")
        if have < file["size"]:
            raise OSError("Kết nối bị ngắt giữa chừng")

    def _verify(self, path: Path, file: dict, index: int, total: int) -> bool:
        title = f"Đang kiểm tra phần {index}/{total} (SHA-256)"
        digest = sha256_of(path, lambda done: self.report(title, done * 100 / file["size"], ""))
        return digest == file["sha256"]

    def _join_parts(self, parts: list[Path]) -> Path:
        if len(parts) == 1:
            return parts[0]
        joined = DOWNLOAD_DIR / f"AutoGuardian-{self.variant}.zip"
        total = sum(p.stat().st_size for p in parts)
        done = 0
        with open(joined, "wb") as out:
            for p in parts:
                with open(p, "rb") as src:
                    while block := src.read(CHUNK * 8):
                        out.write(block)
                        done += len(block)
                        self.report("Đang ghép các phần tải về", done * 100 / total, "")
                p.unlink()
        return joined

    def _extract(self, archive: Path) -> Path:
        staging = INSTALL_ROOT / "_staging"
        shutil.rmtree(longpath(staging), ignore_errors=True)
        with zipfile.ZipFile(archive) as zf:
            members = zf.infolist()
            for i, m in enumerate(members, 1):
                if self.cancel_event.is_set():
                    raise CancelledError()
                zf.extract(m, longpath(staging))
                if i % 20 == 0 or i == len(members):
                    self.report("Đang giải nén", i * 100 / len(members), f"{i}/{len(members)} file")
        app = staging / "AutoGuardian"
        if not (app / "AutoGuardian.exe").exists():
            raise RuntimeError("Gói tải về không hợp lệ (thiếu AutoGuardian.exe).")
        return app

    def _swap_into_place(self, new_app: Path) -> None:
        self.report("Đang hoàn tất cài đặt", -1, "")
        old = INSTALL_ROOT / "_old"
        shutil.rmtree(longpath(old), ignore_errors=True)
        if APP_DIR.exists():
            # Giữ cấu hình (vạch đếm, vùng cấm, ngưỡng...) và dữ liệu (ảnh vi phạm, báo cáo) của người dùng
            for name in USER_DATA_DIRS:
                if (APP_DIR / name).exists():
                    shutil.rmtree(longpath(new_app / name), ignore_errors=True)
                    shutil.copytree(longpath(APP_DIR / name), longpath(new_app / name))
            try:
                os.rename(longpath(APP_DIR), longpath(old))
            except OSError as e:
                raise RuntimeError("Không thể cập nhật vì AutoGuardian đang mở. Hãy đóng ứng dụng rồi thử lại.") from e
        os.rename(longpath(new_app), longpath(APP_DIR))
        shutil.rmtree(longpath(old), ignore_errors=True)
        shutil.rmtree(longpath(INSTALL_ROOT / "_staging"), ignore_errors=True)

    def _create_shortcuts(self) -> None:
        """Shortcut Desktop + Start Menu trỏ tới bản sao launcher (để luôn kiểm tra cập nhật)."""
        target = APP_EXE
        if getattr(sys, "frozen", False):
            try:
                if Path(sys.executable).resolve() != LAUNCHER_COPY.resolve():
                    shutil.copy2(sys.executable, LAUNCHER_COPY)
                target = LAUNCHER_COPY
            except OSError:
                pass
        ps = (
            "$w = New-Object -ComObject WScript.Shell; "
            "foreach ($dir in @([Environment]::GetFolderPath('Desktop'), [Environment]::GetFolderPath('Programs'))) { "
            "  $s = $w.CreateShortcut((Join-Path $dir 'AutoGuardian.lnk')); "
            f"  $s.TargetPath = '{target}'; $s.WorkingDirectory = '{target.parent}'; "
            f"  $s.IconLocation = '{APP_EXE},0'; $s.Description = 'AutoGuardian'; $s.Save() }}"
        )
        subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps],
            capture_output=True, timeout=30, creationflags=CREATE_NO_WINDOW,
        )


# ---------------------------------------------------------------------------
# Giao diện
# ---------------------------------------------------------------------------
class LauncherApp:
    def __init__(self, args: argparse.Namespace) -> None:
        self.args = args
        self.events: "queue.Queue[Callable[[], None]]" = queue.Queue()
        self.installer: Optional[Installer] = None

        self.root = tk.Tk()
        self.root.title("AutoGuardian - Cài đặt & Khởi chạy")
        self.root.geometry("560x300")
        self.root.resizable(False, False)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        self.frame = ttk.Frame(self.root, padding=20)
        self.frame.pack(fill="both", expand=True)
        ttk.Label(self.frame, text="AutoGuardian", font=("Segoe UI", 16, "bold")).pack(anchor="w")
        self.body = ttk.Frame(self.frame)
        self.body.pack(fill="both", expand=True, pady=(10, 0))

        self.root.after(100, self._pump_events)
        self._show_status("Đang kiểm tra phiên bản...")
        threading.Thread(target=self._startup, daemon=True).start()

    # ---- luồng giao diện ------------------------------------------------
    def ui(self, fn: Callable, *a) -> None:
        """Gọi hàm giao diện từ luồng nền một cách an toàn."""
        self.events.put(lambda: fn(*a))

    def _pump_events(self) -> None:
        while not self.events.empty():
            self.events.get_nowait()()
        self.root.after(100, self._pump_events)

    def _clear(self) -> None:
        for w in self.body.winfo_children():
            w.destroy()

    def _show_status(self, text: str) -> None:
        self._clear()
        ttk.Label(self.body, text=text, wraplength=500).pack(anchor="w")

    def _show_progress(self) -> None:
        self._clear()
        self.title_var = tk.StringVar(value="Chuẩn bị tải...")
        self.detail_var = tk.StringVar(value="")
        ttk.Label(self.body, textvariable=self.title_var, wraplength=500).pack(anchor="w")
        self.bar = ttk.Progressbar(self.body, length=500, maximum=100)
        self.bar.pack(pady=10, anchor="w")
        ttk.Label(self.body, textvariable=self.detail_var, foreground="#555").pack(anchor="w")
        ttk.Label(
            self.body, wraplength=500, foreground="#555",
            text="Có thể đóng cửa sổ: lần mở sau sẽ tải tiếp từ chỗ đang dừng.",
        ).pack(anchor="w", pady=(10, 0))
        ttk.Button(self.body, text="Hủy", command=self._on_close).pack(anchor="e", side="bottom")

    def _update_progress(self, title: str, percent: float, detail: str) -> None:
        self.title_var.set(title)
        self.detail_var.set(detail)
        if percent < 0:
            self.bar.configure(mode="indeterminate")
            self.bar.start(15)
        else:
            self.bar.stop()
            self.bar.configure(mode="determinate", value=percent)

    # ---- quy trình -----------------------------------------------------
    def _startup(self) -> None:
        state = None if self.args.reinstall else load_state()
        manifest = fetch_manifest(timeout=5 if state else 15)

        if state:
            newer = manifest and parse_version(manifest["app_version"]) > parse_version(state["version"])
            if newer and state["variant"] in manifest["variants"]:
                self.ui(self._ask_update, manifest, state)
            else:
                self.ui(self._launch)
            return

        if manifest is None:
            self.ui(self._fatal, "Không tải được thông tin phiên bản.\n\n"
                                 "Lần cài đặt đầu tiên cần kết nối Internet. Hãy kiểm tra mạng rồi mở lại.")
            return
        gpu = detect_nvidia_gpu()
        if self.args.variant:
            self.ui(self._start_install, manifest, self.args.variant)
        else:
            self.ui(self._show_choice, manifest, gpu)

    def _show_choice(self, manifest: dict, gpu: Optional[dict]) -> None:
        self._clear()
        variants = manifest["variants"]
        if gpu and gpu["cuda_ok"]:
            info, default = f"Phát hiện GPU: {gpu['name']} (driver {gpu['driver']}). Khuyên dùng bản GPU.", "cuda"
        elif gpu:
            info = (f"Phát hiện GPU: {gpu['name']} nhưng driver {gpu['driver']} quá cũ cho CUDA 12 "
                    f"(cần ≥ {MIN_CUDA12_DRIVER[0]}.{MIN_CUDA12_DRIVER[1]}). Khuyên dùng bản CPU hoặc cập nhật driver.")
            default = "cpu"
        else:
            info, default = "Không phát hiện GPU NVIDIA. Khuyên dùng bản CPU.", "cpu"
        ttk.Label(self.body, text=info, wraplength=500).pack(anchor="w", pady=(0, 10))

        choice = tk.StringVar(value=default)
        for key in ("cuda", "cpu"):
            if key in variants:
                v = variants[key]
                size = human_mb(sum(f["size"] for f in v["files"]))
                ttk.Radiobutton(
                    self.body, variable=choice, value=key,
                    text=f"{v['label']} - tải {size}, cài đặt {human_mb(v['unpacked_size'])}",
                ).pack(anchor="w", pady=2)

        ttk.Label(self.body, text=f"Phiên bản {manifest['app_version']}  |  Cài vào: {INSTALL_ROOT}",
                  foreground="#555", wraplength=500).pack(anchor="w", pady=(10, 0))
        buttons = ttk.Frame(self.body)
        buttons.pack(side="bottom", fill="x")
        ttk.Button(buttons, text="Thoát", command=self.root.destroy).pack(side="right")
        ttk.Button(buttons, text="Cài đặt", command=lambda: self._start_install(manifest, choice.get())).pack(
            side="right", padx=8)

    def _ask_update(self, manifest: dict, state: dict) -> None:
        if messagebox.askyesno(
            "Có bản cập nhật",
            f"Đã có AutoGuardian {manifest['app_version']} (bạn đang dùng {state['version']}).\n"
            "Cập nhật ngay? Cấu hình và dữ liệu của bạn được giữ nguyên.",
        ):
            self._start_install(manifest, state["variant"])
        else:
            self._launch()

    def _start_install(self, manifest: dict, variant: str) -> None:
        self._show_progress()
        self.installer = Installer(
            manifest, variant, lambda t, p, d: self.ui(self._update_progress, t, p, d),
            shortcuts=not self.args.no_shortcuts,
        )
        threading.Thread(target=self._install_worker, daemon=True).start()

    def _install_worker(self) -> None:
        try:
            self.installer.run()
        except CancelledError:
            self.ui(self.root.destroy)
            return
        except Exception as e:
            log_error(e)
            self.ui(self._fatal, f"Cài đặt thất bại:\n\n{e}\n\nChi tiết lỗi: {LOG_FILE}")
            return
        if self.args.no_launch:
            self.ui(self.root.destroy)
        else:
            self.ui(self._launch)

    def _launch(self) -> None:
        self._show_status("Đang mở AutoGuardian...")
        try:
            subprocess.Popen([str(APP_EXE)], cwd=str(APP_DIR), close_fds=True)
        except OSError as e:
            self._fatal(f"Không mở được ứng dụng: {e}\n\nHãy chạy lại launcher với tham số --reinstall.")
            return
        self.root.after(1500, self.root.destroy)

    def _fatal(self, message: str) -> None:
        messagebox.showerror("AutoGuardian", message)
        self.root.destroy()

    def _on_close(self) -> None:
        if self.installer is not None:
            self.installer.cancel_event.set()
            self._show_status("Đang dừng... (phần đã tải được giữ lại)")
        else:
            self.root.destroy()

    def run(self) -> None:
        self.root.mainloop()


def main() -> None:
    parser = argparse.ArgumentParser(description="AutoGuardian Launcher")
    parser.add_argument("--variant", choices=["cpu", "cuda"])
    parser.add_argument("--reinstall", action="store_true")
    parser.add_argument("--no-launch", action="store_true")
    parser.add_argument("--no-shortcuts", action="store_true")
    LauncherApp(parser.parse_args()).run()


if __name__ == "__main__":
    main()

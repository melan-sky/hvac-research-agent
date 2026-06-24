from pathlib import Path
import datetime as _dt
import socket
import subprocess
import sys
import threading
import traceback
import tkinter as tk
from tkinter import messagebox
import webbrowser

from simple_web import create_server


APP_TITLE = "HVAC 系统节能技术检索智能体"


def app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def log(message: str) -> None:
    if os.environ.get("HVAC_AGENT_LOG") != "1":
        return
    try:
        path = app_dir() / "HVAC检索智能体运行日志.txt"
        stamp = _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with path.open("a", encoding="utf-8") as f:
            f.write(f"[{stamp}] {message}\n")
    except Exception:
        pass


def free_port(preferred: int = 8501) -> int:
    for port in [preferred, 8502, 8503, 8510, 0]:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.bind(("127.0.0.1", port))
                return sock.getsockname()[1]
            except OSError:
                continue
    return preferred


def open_app_window(url: str) -> None:
    edge = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")
    if not edge.exists():
        edge = Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe")
    if edge.exists():
        log(f"open edge app: {url}")
        subprocess.Popen([str(edge), f"--app={url}"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return
    log(f"open browser: {url}")
    webbrowser.open(url)


def icon_path() -> Path:
    bundled = app_dir() / "juhuali.ico"
    if bundled.exists():
        return bundled
    local = Path(__file__).resolve().parent / "juhuali.ico"
    return local


class DesktopApp:
    def __init__(self) -> None:
        log("desktop app starting")
        self.closed = False
        self.port = free_port()
        self.url = f"http://127.0.0.1:{self.port}"
        log(f"selected port: {self.port}")
        self.server = create_server("127.0.0.1", self.port)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        log("http server started")

        self.root = tk.Tk()
        self.root.title(APP_TITLE)
        try:
            self.root.iconbitmap(str(icon_path()))
        except Exception:
            pass
        self.root.geometry("520x280")
        self.root.resizable(False, False)
        self.root.configure(bg="#f5f7fb")
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.root.after(1000, self.keep_alive)

        title = tk.Label(
            self.root,
            text=APP_TITLE,
            bg="#f5f7fb",
            fg="#172033",
            font=("Microsoft YaHei", 18, "bold"),
        )
        title.pack(anchor="w", padx=28, pady=(28, 8))

        desc = tk.Label(
            self.root,
            text="这是可分发的 Windows 应用。双击后会在本机启动检索服务，并打开独立应用窗口。\n如果要发一个网址给别人直接用，需要另行部署公网网站版。",
            bg="#f5f7fb",
            fg="#657083",
            justify="left",
            font=("Microsoft YaHei", 10),
        )
        desc.pack(anchor="w", padx=30, pady=(0, 18))

        self.status = tk.Label(
            self.root,
            text=f"服务已启动：{self.url}",
            bg="#eef4fb",
            fg="#223a59",
            font=("Microsoft YaHei", 10),
            padx=12,
            pady=8,
        )
        self.status.pack(anchor="w", padx=30, pady=(0, 20))

        buttons = tk.Frame(self.root, bg="#f5f7fb")
        buttons.pack(anchor="w", padx=30)

        open_btn = tk.Button(
            buttons,
            text="打开检索界面",
            command=lambda: open_app_window(self.url),
            bg="#223a59",
            fg="white",
            activebackground="#344e72",
            activeforeground="white",
            relief="flat",
            font=("Microsoft YaHei", 11, "bold"),
            padx=20,
            pady=8,
        )
        open_btn.pack(side="left", padx=(0, 12))

        copy_btn = tk.Button(
            buttons,
            text="复制本机地址",
            command=self.copy_url,
            bg="#ffffff",
            fg="#223a59",
            relief="solid",
            borderwidth=1,
            font=("Microsoft YaHei", 10),
            padx=18,
            pady=8,
        )
        copy_btn.pack(side="left")

        open_app_window(self.url)
        self.root.withdraw()

    def keep_alive(self) -> None:
        if self.closed:
            return
        try:
            self.root.after(1000, self.keep_alive)
        except Exception:
            log(traceback.format_exc())

    def copy_url(self) -> None:
        self.root.clipboard_clear()
        self.root.clipboard_append(self.url)
        messagebox.showinfo(APP_TITLE, "已复制本机访问地址。")

    def close(self) -> None:
        self.closed = True
        log("desktop app closing")
        try:
            self.server.shutdown()
        finally:
            self.root.destroy()

    def run(self) -> None:
        log("tk mainloop enter")
        self.root.mainloop()
        log("tk mainloop exit")


if __name__ == "__main__":
    try:
        DesktopApp().run()
    except Exception:
        log(traceback.format_exc())
        raise

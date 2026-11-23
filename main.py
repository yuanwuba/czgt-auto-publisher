"""Desktop control panel: 启动 / 停止 / 关闭 + 08:00-10:00 auto schedule."""
from __future__ import annotations

import json
import threading
import time
import tkinter as tk
from datetime import datetime, time as dtime
from pathlib import Path

from automation import Automator

BASE = Path(__file__).resolve().parent
CONTROL = BASE / "control.json"


class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("创作罐头 自动化控制台")
        self.root.geometry("320x240+40+40")
        self.root.attributes("-topmost", True)
        self.cfg = json.loads((BASE / "config.json").read_text(encoding="utf-8"))
        self.automator = Automator()
        self.stop_event = threading.Event()
        self.worker = None
        self.running = False
        self.status = tk.StringVar(value="就绪（等待 08:00 自动开始）")
        self._build_ui()
        self.root.after(1000, self.tick)

    def _build_ui(self):
        tk.Label(self.root, text="创作罐头 · 今日头条自动发布", font=("Microsoft YaHei", 11, "bold")).pack(pady=10)
        tk.Label(self.root, textvariable=self.status, wraplength=290, justify="left", fg="#444").pack(pady=5)
        f = tk.Frame(self.root)
        f.pack(pady=12)
        tk.Button(f, text="启动", width=8, command=self.start).grid(row=0, column=0, padx=5)
        tk.Button(f, text="停止", width=8, command=self.stop).grid(row=0, column=1, padx=5)
        tk.Button(f, text="关闭", width=8, command=self.close).grid(row=0, column=2, padx=5)
        tk.Label(self.root, text="自动运行：每天 08:00 - 10:00", fg="#888").pack(side="bottom", pady=8)

    def _in_window(self) -> bool:
        now = datetime.now().time()
        sh, sm = map(int, self.cfg["work_start"].split(":"))
        eh, em = map(int, self.cfg["work_end"].split(":"))
        return dtime(sh, sm) <= now <= dtime(eh, em)

    def _error_from_worker(self, kind: str, msg: str):
        def show():
            self.stop()
            if kind == "login":
                tk.messagebox.showwarning("需要登录", msg + "\n\n请先手动登录创作罐头，再点击“启动”。")
            else:
                tk.messagebox.showerror("运行错误", msg)
        self.root.after(0, show)

    def start(self):
        if self.running:
            return
        self.stop_event.clear()
        self.running = True
        self.status.set("运行中：正在执行发布流程…")
        self.worker = threading.Thread(
            target=self.automator.run_until_stopped,
            args=(self.stop_event, self._error_from_worker),
            daemon=True,
        )
        self.worker.start()

    def stop(self):
        self.stop_event.set()
        self.running = False
        self.status.set("已停止")

    def close(self):
        self.stop()
        self.root.destroy()

    def tick(self):
        if CONTROL.exists():
            try:
                cmd = CONTROL.read_text(encoding="utf-8").strip()
            except Exception:
                cmd = ""
            CONTROL.write_text("", encoding="utf-8")
            if cmd == "start":
                self.start()
            elif cmd == "stop":
                self.stop()
            elif cmd == "close":
                self.close()
                return
        if self._in_window() and not self.running:
            self.start()
        elif not self._in_window() and self.running:
            self.stop()
            self.status.set("已到 10:00，自动结束")
        self.root.after(1000, self.tick)


def main():
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()

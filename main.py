"""Desktop control panel: 启动 / 停止 / 关闭 + 08:00-10:00 auto schedule."""
from __future__ import annotations

import json
import queue
import sys
import threading
from datetime import datetime, time as dtime
from pathlib import Path

from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import (
    QApplication, QHBoxLayout, QLabel, QMessageBox, QPushButton, QVBoxLayout, QWidget,
)

from automation import Automator

BASE = Path(__file__).resolve().parent
CONTROL = BASE / "control.json"


class Panel(QWidget):
    def __init__(self):
        super().__init__()
        self.cfg = json.loads((BASE / "config.json").read_text(encoding="utf-8"))
        self.automator = Automator()
        self.stop_event = threading.Event()
        self.worker = None
        self.running = False
        self.errors = queue.Queue()
        self.setWindowTitle("创作罐头 自动化控制台")
        self.setGeometry(60, 60, 360, 230)
        self.setWindowFlags(self.windowFlags() | 0x00000008)  # WindowStaysOnTopHint

        layout = QVBoxLayout()
        layout.addWidget(QLabel("创作罐头 · 今日头条自动发布"))
        self.status = QLabel("就绪（等待 08:00 自动开始）")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)

        row = QHBoxLayout()
        self.btn_start = QPushButton("启动")
        self.btn_stop = QPushButton("停止")
        self.btn_close = QPushButton("关闭")
        self.btn_start.clicked.connect(self.start)
        self.btn_stop.clicked.connect(self.stop)
        self.btn_close.clicked.connect(self.close_app)
        row.addWidget(self.btn_start)
        row.addWidget(self.btn_stop)
        row.addWidget(self.btn_close)
        layout.addLayout(row)
        layout.addWidget(QLabel("自动运行：每天 08:00 - 10:00"))
        self.setLayout(layout)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(1000)

    def _in_window(self) -> bool:
        now = datetime.now().time()
        sh, sm = map(int, self.cfg["work_start"].split(":"))
        eh, em = map(int, self.cfg["work_end"].split(":"))
        return dtime(sh, sm) <= now <= dtime(eh, em)

    def _worker_error(self, kind: str, msg: str):
        self.errors.put((kind, msg))

    def start(self):
        if self.running:
            return
        self.stop_event.clear()
        self.running = True
        self.status.setText("运行中：正在执行发布流程…")
        self.worker = threading.Thread(
            target=self.automator.run_until_stopped,
            args=(self.stop_event, self._worker_error),
            daemon=True,
        )
        self.worker.start()

    def stop(self):
        self.stop_event.set()
        self.running = False
        self.status.setText("已停止")

    def close_app(self):
        self.stop()
        self.close()
        QApplication.instance().quit()

    def tick(self):
        while not self.errors.empty():
            kind, msg = self.errors.get()
            self.stop()
            if kind == "login":
                QMessageBox.warning(self, "需要登录", msg + "\n\n请先手动登录创作罐头，再点击“启动”。")
            else:
                QMessageBox.critical(self, "运行错误", msg)

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
                self.close_app()
                return

        if self._in_window() and not self.running:
            self.start()
        elif not self._in_window() and self.running:
            self.stop()
            self.status.setText("已到 10:00，自动结束")


def main():
    app = QApplication(sys.argv)
    w = Panel()
    w.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()

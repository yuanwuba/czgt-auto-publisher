"""Create desktop control buttons and an optional daily 08:00 scheduled task."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
DESKTOP = Path(os.environ.get("USERPROFILE", str(Path.home()))) / "Desktop"
CONTROL = BASE / "control.json"


def bat(name: str, cmd: str):
    path = DESKTOP / f"{name}.bat"
    content = (
        "@echo off\n"
        f'echo {cmd} > "{CONTROL}"\n'
    )
    path.write_text(content, encoding="gbk")
    print("created", path)


def main():
    DESKTOP.mkdir(parents=True, exist_ok=True)
    bat("启动创作罐头自动化", "start")
    bat("停止创作罐头自动化", "stop")
    bat("关闭创作罐头自动化", "close")

    task_name = "CZGT_Daily_Auto"
    main_py = BASE / "main.py"
    tr = '"{}" "{}"'.format(sys.executable, main_py)
    try:
        subprocess.run(
            ["schtasks", "/Create", "/TN", task_name, "/TR", tr,
             "/SC", "DAILY", "/ST", "08:00", "/F"],
            check=True, capture_output=True, text=True,
        )
        print("scheduled task created:", task_name)
    except Exception as e:
        print("schedule task not created (manual panel still works):", e)


if __name__ == "__main__":
    main()

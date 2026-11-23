"""GUI automation engine for 创作罐头 -> 今日头条 publishing workflow."""
from __future__ import annotations

import json
import logging
import os
import random
import subprocess
import time
from pathlib import Path

import pyautogui
import pygetwindow as gw

BASE = Path(__file__).resolve().parent
CONFIG_PATH = BASE / "config.json"
LOG_PATH = BASE / "automation.log"

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.15


class LoginRequired(RuntimeError):
    pass


class ConfigMissing(RuntimeError):
    pass


class Automator:
    def __init__(self, config_path: Path = CONFIG_PATH):
        self.cfg = json.loads(config_path.read_text(encoding="utf-8"))
        self.logger = logging.getLogger("czgt.automation")
        if not self.logger.handlers:
            h = logging.FileHandler(LOG_PATH, encoding="utf-8")
            h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
            self.logger.addHandler(h)
            self.logger.setLevel(logging.INFO)
        self.window = None

    # ---------- basic helpers ----------
    def log(self, msg: str, level: int = logging.INFO):
        self.logger.log(level, msg)

    def find_window(self):
        title_key = self.cfg.get("window_title_contains", "创作罐头")
        for w in gw.getAllWindows():
            if title_key in w.title and w.width > 400:
                return w
        return None

    def ensure_app(self):
        self.window = self.find_window()
        if self.window is None:
            app = self.cfg["app_path"]
            if not os.path.exists(app):
                raise RuntimeError(f"找不到程序: {app}")
            exe_direct = os.path.join(os.path.dirname(app), "1.8.3", "创作罐头.exe")
            candidates = [app]
            if os.path.exists(exe_direct):
                candidates.append(exe_direct)
            for candidate in candidates:
                self.log(f"启动 {candidate}")
                subprocess.Popen([candidate], cwd=os.path.dirname(candidate))
                deadline = time.time() + 30
                while time.time() < deadline:
                    time.sleep(1)
                    self.window = self.find_window()
                    if self.window:
                        break
                if self.window:
                    break
            if self.window is None:
                raise RuntimeError(
                    "创作罐头窗口未能打开。请手动启动一次程序；如果仍无法启动，建议注销/重启 Windows 后重试"
                )
        try:
            self.window.activate()
        except Exception:
            pass
        time.sleep(1)
        self.log(f"已激活窗口: {self.window.title}")
        return self.window

    def template_path(self, name: str) -> Path | None:
        rel = self.cfg["steps"].get(name, {}).get("image", "")
        if not rel:
            return None
        p = BASE / rel
        return p if p.exists() else None

    def locate_template(self, name: str):
        p = self.template_path(name)
        if p is None:
            return None
        try:
            return pyautogui.locateOnScreen(str(p), grayscale=True)
        except Exception:
            return None

    def click_step(self, name: str, required: bool = True):
        box = self.locate_template(name)
        if box:
            pyautogui.click(pyautogui.center(box))
            self.log(f"点击模板 {name}")
            return True
        s = self.cfg["steps"].get(name, {})
        x, y = int(s.get("x", 0)), int(s.get("y", 0))
        if x > 0 and y > 0:
            pyautogui.click(x, y)
            self.log(f"点击坐标 {name} ({x},{y})")
            return True
        if required:
            raise ConfigMissing(f"步骤 {name} 未配置坐标或模板，请先运行 calibrate.py")
        return False

    def wait_step(self, name: str, timeout: int = 30):
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self.locate_template(name) is not None:
                return True
            s = self.cfg["steps"].get(name, {})
            if s.get("x", 0) > 0 and s.get("y", 0) > 0:
                return True
            time.sleep(0.5)
        return False

    def check_login(self):
        # Customise by adding templates/login_prompt.png from your own screen.
        p = BASE / "templates" / "login_prompt.png"
        if p.exists():
            try:
                if pyautogui.locateOnScreen(str(p), grayscale=True):
                    raise LoginRequired("创作罐头未登录，请先手动登录后再启动自动化")
            except LoginRequired:
                raise
            except Exception:
                pass
        self.log("登录状态检查完成（未发现登录提示）")

    # ---------- workflow ----------
    def open_hot_viral(self):
        self.click_step("hot_material")
        time.sleep(1)
        if not self.click_step("all_viral", required=False):
            self.log("全网爆文入口未配置，尝试使用页面内文字查找失败；请运行 calibrate.py", logging.WARNING)
            raise ConfigMissing("all_viral")
        time.sleep(1.5)

    def set_filters(self):
        options = self.cfg.get("filter_options", {
            "platform_dropdown": 1,
            "content_type_dropdown": 2,
            "field_dropdown": 0,
            "reads_dropdown": 0,
            "time_dropdown": 1,
            "sort_dropdown": 1,
        })
        for key, index in options.items():
            if not self.click_step(key, required=False):
                self.log(f"筛选控件 {key} 未配置，跳过", logging.WARNING)
                continue
            pyautogui.press("home")
            for _ in range(int(index)):
                pyautogui.press("down")
            pyautogui.press("enter")
            time.sleep(0.4)
        self.log("筛选条件已尝试设置")

    def create_short_graphic(self):
        self.click_step("first_title", required=False)
        time.sleep(0.6)
        self.click_step("ai_create")
        time.sleep(0.8)
        self.click_step("send_short_graphic")
        time.sleep(2)

    def wait_images_and_upload(self):
        time.sleep(int(self.cfg.get("cycle_delay_seconds", 3)))
        self.click_step("pick_image", required=False)
        self.click_step("next_arrow", required=False)
        upload_file = self.cfg.get("upload_file", "")
        if self.click_step("upload_file", required=False) and upload_file:
            time.sleep(0.8)
            pyautogui.write(upload_file, interval=0.005)
            pyautogui.press("enter")
            time.sleep(1)
        self.log("图文生成/上传步骤已尝试")

    def insert_editor(self):
        self.click_step("insert_editor")
        time.sleep(2)
        self.log("已进入编辑器界面")

    def publish_or_fallback(self):
        self.click_step("select_account")
        time.sleep(1)
        count = int(self.cfg.get("account_count", 3))
        # random account from popup using arrow keys
        for _ in range(random.randint(0, max(0, count - 1))):
            pyautogui.press("down")
        pyautogui.press("enter")
        time.sleep(0.8)
        self.click_step("publish")
        time.sleep(3)

        # detect "copy success" / works management fallback
        fallback = False
        p = BASE / "templates" / "copy_success.png"
        if p.exists():
            try:
                fallback = pyautogui.locateOnScreen(str(p), grayscale=True) is not None
            except Exception:
                fallback = False
        if self.locate_template("works_manage"):
            fallback = True
        if fallback:
            self.log("检测到复制成功/作品管理，进入微头条兜底流程")
            self.click_step("works_manage", required=False)
            self.click_step("weitoutiao_tab")
            time.sleep(1.5)
            self.click_step("weitoutiao_textarea")
            pyautogui.hotkey("ctrl", "v")
            time.sleep(0.5)
            self.click_step("publish")
            time.sleep(2)
        self.log("发布流程已执行，请人工核实结果")

    def run_once(self) -> bool:
        try:
            self.ensure_app()
            self.check_login()
            self.open_hot_viral()
            self.set_filters()
            self.create_short_graphic()
            self.wait_images_and_upload()
            self.insert_editor()
            self.publish_or_fallback()
            return True
        except LoginRequired as e:
            self.log(str(e), logging.ERROR)
            raise
        except Exception as e:
            self.log(f"本轮失败: {e}", logging.ERROR)
            return False

    def run_until_stopped(self, stop_event, on_error=None):
        while not stop_event.is_set():
            try:
                ok = self.run_once()
            except LoginRequired as e:
                if on_error:
                    on_error("login", str(e))
                return
            except Exception as e:
                if on_error:
                    on_error("error", str(e))
                ok = False
            if not ok:
                time.sleep(int(self.cfg.get("retry_seconds", 10)))
            else:
                time.sleep(1)

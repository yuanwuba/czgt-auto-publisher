"""GUI automation engine for 创作罐头 -> 今日头条 publishing workflow."""
from __future__ import annotations

import json
import logging
import os
import random
import subprocess
import time
from pathlib import Path

import ctypes

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
        self.focus_window()
        return self.window

    def focus_window(self):
        """把创作罐头切到前台并最大化。pygetwindow.activate() 在 Edge 抢焦点时会失败，
        这里用 Alt 键技巧绕过 Windows 前台锁定，再调用 SetForegroundWindow。"""
        self.window = self.window or self.find_window()
        if self.window is None:
            return False
        try:
            # 最小化抢焦点的浏览器窗口（如 Edge），避免它反复抢前台
            for w in gw.getAllWindows():
                if w.title and w.title != self.window.title and (
                    "Edge" in w.title or "Microsoft" in w.title
                ) and not w.isMinimized:
                    try:
                        w.minimize()
                    except Exception:
                        pass
            h = self.window._hWnd
            u = ctypes.windll.user32
            u.ShowWindow(h, 3)  # SW_MAXIMIZE
            pyautogui.keyDown("alt")
            pyautogui.keyUp("alt")
            u.BringWindowToTop(h)
            u.SetForegroundWindow(h)
            time.sleep(0.8)
            active = gw.getActiveWindow()
            if active and self.cfg.get("window_title_contains", "创作罐头") in active.title:
                self.log(f"已激活窗口: {active.title}")
                return True
        except Exception as e:
            self.log(f"激活窗口异常: {e}", logging.WARNING)
        try:
            self.window.activate()
        except Exception:
            pass
        return False

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
        has_template = self.template_path(name) is not None
        while time.time() < deadline:
            if self.locate_template(name) is not None:
                return True
            if not has_template:
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
            self.log("全网爆文入口未配置，请运行 calibrate.py", logging.WARNING)
            raise ConfigMissing("all_viral")
        time.sleep(2)
        data_wait = int(self.cfg.get("data_wait_seconds", 12))
        self.wait_step("ai_create", data_wait)
        time.sleep(1)

    def set_filters(self):
        if self.cfg.get("skip_filters", False):
            self.log("筛选条件已是默认值（今日头条/短图文/全部/全部/1天内/阅读量排序），跳过")
            return
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
        # 第一行 AI创作 -> 发短图文 -> 等选题生成
        self.click_step("ai_create")
        time.sleep(1.2)
        self.click_step("send_short_graphic")
        self.log("已进入发短图文，等待 5 篇选题生成…")
        time.sleep(int(self.cfg.get("outline_wait_seconds", 16)))

    def wait_images_and_upload(self):
        # 选第一篇选题 -> 点发送箭头 -> 等完整文章生成
        self.click_step("pick_image", required=False)
        time.sleep(1)
        self.click_step("next_arrow", required=False)
        upload_file = self.cfg.get("upload_file", "")
        if upload_file and self.click_step("upload_file", required=False):
            time.sleep(0.8)
            pyautogui.write(upload_file, interval=0.005)
            pyautogui.press("enter")
            time.sleep(1)
        wait = int(self.cfg.get("generation_wait_seconds", 100))
        self.log(f"等待 AI 生成完整文章（{wait}秒）…")
        time.sleep(wait)

    def _zoom_out(self, steps: int = 4):
        pyautogui.keyDown("ctrl")
        pyautogui.moveTo(960, 500)
        pyautogui.scroll(-steps)
        pyautogui.keyUp("ctrl")
        time.sleep(0.8)

    def _zoom_in(self, steps: int = 4):
        pyautogui.keyDown("ctrl")
        pyautogui.moveTo(960, 500)
        pyautogui.scroll(steps)
        pyautogui.keyUp("ctrl")
        time.sleep(0.8)

    def insert_editor(self):
        """生成完成后，文章卡片在面板底部、被输入区遮挡。先缩小界面 Ctrl+滚轮，
        滚动到对话底部露出“插入编辑器”，点击后再恢复缩放。"""
        self._zoom_out(4)
        pyautogui.moveTo(1600, 700)
        pyautogui.scroll(-30)  # 滚到对话底部
        time.sleep(1.2)
        box = self.locate_template("insert_editor")
        if box:
            pyautogui.click(pyautogui.center(box))
            self.log("点击模板 插入编辑器")
        else:
            s = self.cfg["steps"].get("insert_editor", {})
            if not (s.get("x", 0) > 0 and s.get("y", 0) > 0):
                self._zoom_in(4)
                self.log("未找到“插入编辑器”按钮", logging.WARNING)
                return False
            pyautogui.click(int(s["x"]), int(s["y"]))
            self.log(f"点击坐标 插入编辑器 ({s['x']},{s['y']})")
        time.sleep(2)
        self._zoom_in(4)  # 恢复缩放，后续编辑器坐标基于标准缩放
        self.log("已进入编辑器界面")
        return True

    def publish_or_fallback(self):
        """实测流程：编辑器底部“选择账号发布” -> 随机选账号 -> 创作罐头复制全文并
        打开微头条发布页 -> 页面正文常为空，需点输入框清空后 Ctrl+V 粘贴 -> 点“发布”。"""
        if not self.click_step("select_account", required=False):
            self.log("未找到“选择账号发布”按钮，请运行 calibrate.py", logging.WARNING)
            return False
        time.sleep(1.2)
        positions = self.cfg.get("account_positions", [])
        if positions:
            x, y = random.choice(positions)
            pyautogui.click(int(x), int(y))
            self.log(f"已随机选择账号 ({x},{y})")
        else:
            if not self.click_step("account_item", required=False):
                self.log("未配置账号位置", logging.WARNING)
                return False
        time.sleep(6)  # 等待跳转到微头条发布页

        # 关键：选账号后正文通常为空，必须把剪贴板里的全文粘贴进输入框
        if not self.click_step("weitoutiao_textarea", required=False):
            self.log("未找到微头条输入框，尝试兜底入口", logging.WARNING)
            self.click_step("works_manage", required=False)
            time.sleep(2)
            if not self.click_step("weitoutiao_tab", required=False):
                self.log("未找到微头条标签", logging.WARNING)
                return False
            time.sleep(2)
            self.click_step("weitoutiao_textarea")
        time.sleep(0.5)
        pyautogui.hotkey("ctrl", "a")
        pyautogui.press("delete")
        time.sleep(0.3)
        pyautogui.hotkey("ctrl", "v")
        time.sleep(1)
        self.log("已将全文粘贴到微头条输入框")

        self.click_step("publish")
        time.sleep(3)
        self.log("已点击微头条“发布”按钮，请到作品管理核实结果")
        return True

    def run_once(self) -> bool:
        try:
            self.ensure_app()
            self.check_login()
            self.open_hot_viral()
            self.set_filters()
            self.create_short_graphic()
            self.wait_images_and_upload()
            if not self.insert_editor():
                return False
            return self.publish_or_fallback()
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

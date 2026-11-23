"""Calibrate click positions for screens that are not visible in the recorded screenshots."""
from __future__ import annotations

import json
import time
from pathlib import Path

import pyautogui

BASE = Path(__file__).resolve().parent
CFG = BASE / "config.json"

STEPS = [
    "hot_material", "all_viral", "platform_dropdown", "content_type_dropdown",
    "field_dropdown", "reads_dropdown", "time_dropdown", "sort_dropdown",
    "first_title", "ai_create", "send_short_graphic", "pick_image",
    "next_arrow", "upload_file", "insert_editor", "select_account",
    "account_item", "publish", "works_manage", "weitoutiao_tab",
    "weitoutiao_textarea",
]

LABELS = {
    "hot_material": "左侧「热门素材」入口",
    "all_viral": "「全网爆文」菜单项",
    "platform_dropdown": "媒体平台下拉框",
    "content_type_dropdown": "内容类型下拉框",
    "field_dropdown": "内容领域下拉框",
    "reads_dropdown": "阅读量下拉框",
    "time_dropdown": "发布时间下拉框",
    "sort_dropdown": "内容排序下拉框",
    "first_title": "第一条标题",
    "ai_create": "标题后的「AI创作」按钮",
    "send_short_graphic": "AI创作菜单里的「发短图文」",
    "pick_image": "生成的5篇图文中任选一篇",
    "next_arrow": "图文下方的箭头",
    "upload_file": "「上传文件」按钮",
    "insert_editor": "「插入编辑器」按钮",
    "select_account": "「选择账号发布」按钮",
    "account_item": "账号菜单中的任一账号",
    "publish": "「发布」按钮",
    "works_manage": "作品管理页面入口",
    "weitoutiao_tab": "作品管理左侧「微头条」",
    "weitoutiao_textarea": "微头条输入框「有什么新鲜事想告诉大家？」",
}


def main():
    cfg = json.loads(CFG.read_text(encoding="utf-8"))
    for step in STEPS:
        print(f"\n请把鼠标移到：{LABELS.get(step, step)}")
        print("5 秒后记录位置（期间不要移动鼠标）…")
        time.sleep(5)
        x, y = pyautogui.position()
        cfg["steps"][step]["x"] = x
        cfg["steps"][step]["y"] = y
        CFG.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"已记录 {step} = ({x}, {y})")
    print("\n校准完成。可以运行 install.py 创建桌面按钮。")


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""把 HTML 原型与结构图批量导出为 2 倍高清 PNG。"""
import os
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent          # 交付物/
OUT = ROOT / "export"
OUT.mkdir(parents=True, exist_ok=True)

PROTO = (ROOT / "prototype" / "index.html").as_uri()

SCREENS = [
    (1, "01-工作台"),
    (2, "02-分析进行中"),
    (3, "03-报告详情"),
    (4, "04-报告列表"),
    (5, "05-数据采集"),
    (6, "06-系统设置"),
]

DIAGRAMS = [
    ("diagrams/01-业务流程图.html", "07-业务流程图"),
    ("diagrams/02-系统功能结构图.html", "08-系统功能结构图"),
    ("diagrams/03-角色功能图.html", "09-角色功能图"),
]


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()

        # ---- 原型页面：1440x900 ----
        ctx = browser.new_context(viewport={"width": 1440, "height": 900},
                                  device_scale_factor=2)
        page = ctx.new_page()
        for idx, name in SCREENS:
            page.goto(f"{PROTO}?s={idx}", wait_until="networkidle")
            page.wait_for_timeout(350)
            target = page.locator(f'.screen[data-s="{idx}"]')
            path = OUT / f"{name}.png"
            target.screenshot(path=str(path))
            print(f"[OK] {path.name}")
        ctx.close()

        # ---- 结构图：1600x1000 ----
        ctx2 = browser.new_context(viewport={"width": 1600, "height": 1000},
                                   device_scale_factor=2)
        page2 = ctx2.new_page()
        for rel, name in DIAGRAMS:
            url = (ROOT / rel).as_uri()
            page2.goto(url, wait_until="networkidle")
            page2.wait_for_timeout(350)
            path = OUT / f"{name}.png"
            page2.locator(".canvas").screenshot(path=str(path))
            print(f"[OK] {path.name}")
        ctx2.close()

        browser.close()
    print("全部导出完成 ->", OUT)


if __name__ == "__main__":
    main()

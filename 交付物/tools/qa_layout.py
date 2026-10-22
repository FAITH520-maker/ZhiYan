# -*- coding: utf-8 -*-
"""布局自检：检测元素重叠、文字溢出、画布越界。"""
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
PROTO = (ROOT / "prototype" / "index.html").as_uri()

JS_CHECK = r"""
(sel) => {
  const out = {overflow: [], overlap: []};
  const els = [...document.querySelectorAll(sel)];
  const rects = els.map(e => ({e, r: e.getBoundingClientRect()}));

  // 文字溢出
  for (const {e, r} of rects) {
    if (e.scrollHeight > e.clientHeight + 2 || e.scrollWidth > e.clientWidth + 2) {
      out.overflow.push({cls: e.className, txt: (e.innerText||'').slice(0,28).replace(/\n/g,'/')});
    }
  }
  // 两两重叠（仅同层级盒子）
  for (let i = 0; i < rects.length; i++) {
    for (let j = i + 1; j < rects.length; j++) {
      const a = rects[i].r, b = rects[j].r;
      const ox = Math.min(a.right, b.right) - Math.max(a.left, b.left);
      const oy = Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top);
      if (ox > 4 && oy > 4) {
        out.overlap.push([rects[i].e.innerText.slice(0,20).replace(/\n/g,'/'),
                          rects[j].e.innerText.slice(0,20).replace(/\n/g,'/')]);
      }
    }
  }
  out.scroll = [document.documentElement.scrollWidth, document.documentElement.scrollHeight];
  return out;
}
"""

CASES = [
    (f"{PROTO}?s={i}", f"屏幕{i}", 1440, 900, ".flowbox, .card, .eng")
    for i in range(1, 7)
] + [
    ((ROOT / "diagrams/01-业务流程图.html").as_uri(), "业务流程图", 1600, 1000, ".flowbox"),
    ((ROOT / "diagrams/02-系统功能结构图.html").as_uri(), "功能结构图", 1600, 1000, ".node, .M, .L"),
    ((ROOT / "diagrams/03-角色功能图.html").as_uri(), "角色功能图", 1600, 1000, ".node, .role, .fn"),
]


def main():
    bad = 0
    with sync_playwright() as p:
        b = p.chromium.launch()
        for url, name, w, h, sel in CASES:
            ctx = b.new_context(viewport={"width": w, "height": h})
            pg = ctx.new_page()
            pg.goto(url, wait_until="networkidle")
            pg.wait_for_timeout(250)
            r = pg.evaluate(JS_CHECK, sel)
            sw, sh = r["scroll"]
            status = []
            if r["overflow"]:
                status.append(f"文字溢出 {len(r['overflow'])} 处")
                for o in r["overflow"][:4]:
                    status.append(f"    · {o['txt']}")
            if r["overlap"]:
                status.append(f"盒子重叠 {len(r['overlap'])} 处")
                for o in r["overlap"][:4]:
                    status.append(f"    · {o[0]} × {o[1]}")
            if sw > w + 2 or sh > h + 2:
                status.append(f"画布越界 {sw}x{sh} (期望 {w}x{h})")
            if status:
                bad += 1
                print(f"[!] {name}:")
                for s in status:
                    print("   ", s)
            else:
                print(f"[OK] {name}  无重叠 / 无溢出 / 无越界")
            ctx.close()
        b.close()
    print(f"\n结论：{len(CASES)-bad}/{len(CASES)} 张通过")


if __name__ == "__main__":
    main()

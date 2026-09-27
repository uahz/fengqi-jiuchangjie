#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""截图验收：把游戏各状态渲染成 PNG，供人工/自动核对视觉效果。

原理：在目标 HTML 所在目录生成临时 harness（追加一段驱动脚本），
用 Edge headless 截图，最后把 harness 移出到 _build/harness/。
"""
import os, shutil, subprocess, sys, glob
from pathlib import Path

EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
ROOT = Path("C:/Users/Administrator/WorkBuddy/狂飙game")
OUT = ROOT / "_shots_new"
HARNESS = ROOT / "_build" / "harness"

WEB = ROOT / "01-网页版（写实电影感）" / "fengqi-jiuchangjie.html"
PWA = ROOT / "02-安卓版PWA（写实电影感）" / "index.html"

# 把台词推到底、让选项渲染出来的辅助脚本
ADV = ("var _n=0;var _t=setInterval(function(){"
       "var c=document.getElementById('choices');"
       "if((c&&c.children.length)||_n++>14){clearInterval(_t);return;}"
       "document.getElementById('dlg').click();},200);")

# 状态 -> 注入脚本（在 load 之后执行）
STATES = {
    "01-title": "",
    "02-story": "window.__goto('c1_1');setTimeout(function(){" + ADV + "},300);",
    "03-choice": "window.__goto('c1_2');setTimeout(function(){" + ADV + "},300);",
    "04-card": "window.__goto('c1_8');setTimeout(function(){" + ADV + "},300);",
    "05-rain": "window.__goto('c1_7');setTimeout(function(){" + ADV + "},300);",
    "06-wave": "window.__goto('c1_10');",
    "07-gallery": "window.__goto('c1_1');setTimeout(function(){showGallery('end')},120);",
    "08-panel": "window.__goto('c1_1');setTimeout(function(){openPanel('aff')},120);",
    "09-ending": "window.__goto('c4_4');setTimeout(function(){" + ADV + "},300);",
}

VIEWS = {
    "desk": (1440, 900),
    "mob": (390, 844),
}


def make_harness(target: Path, inject: str, name: str) -> Path:
    html = target.read_text(encoding="utf-8")
    extra = ""
    if inject:
        extra = ("<script>window.addEventListener('load',function(){setTimeout(function(){try{"
                 + inject + "}catch(e){}},180)});</script>")
    html = html.replace("</body>", extra + "\n</body>", 1)
    p = target.parent / f"_shot_{name}.html"
    p.write_text(html, encoding="utf-8")
    return p


def shoot(page: Path, out: Path, w: int, h: int, budget=9000):
    url = page.as_uri()
    cmd = [EDGE, "--headless=new", "--disable-gpu", "--hide-scrollbars",
           "--force-device-scale-factor=1",
           f"--virtual-time-budget={budget}",
           f"--window-size={w},{h}",
           f"--screenshot={out}", url]
    subprocess.run(cmd, capture_output=True, timeout=120)


def main():
    only = sys.argv[1] if len(sys.argv) > 1 else "all"
    OUT.mkdir(parents=True, exist_ok=True)
    HARNESS.mkdir(parents=True, exist_ok=True)
    targets = []
    if only in ("all", "web"):
        targets.append(("web", WEB))
    if only in ("all", "pwa"):
        targets.append(("pwa", PWA))
    made = []
    for tag, tgt in targets:
        views = ["desk"] if tag == "web" else ["mob"]
        for sname, inject in STATES.items():
            hs = make_harness(tgt, inject, f"{tag}_{sname}")
            made.append(hs)
            for vname in views:
                w, h = VIEWS[vname]
                out = OUT / f"{tag}-{sname}-{vname}.png"
                shoot(hs, out, w, h)
                print(f"  {out.name}  {out.stat().st_size//1024 if out.exists() else 'FAIL'} KB")
    # harness 移出发布目录
    for f in made:
        if f.exists():
            shutil.move(str(f), str(HARNESS / f.name))
    print("done")


if __name__ == "__main__":
    main()

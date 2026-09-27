#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""收尾：整理截图、清理旧产物、重命名目录。"""
import os, shutil, glob
from PIL import Image

ROOT = "C:/Users/Administrator/WorkBuddy/狂飙game"
SHOTS = os.path.join(ROOT, "_shots_new")
OLD = os.path.join(ROOT, "_build", "old")
DST = os.path.join(ROOT, "07-截图")

# 源截图 -> 目标文件名   （None 表示不做缩放宽）
SHOT_MAP = [
    ("web-01-title-desk",   "01-网页版-标题.png",           1280),
    ("web-03-choice-desk",  "02-网页版-对话与抉择.png",      1280),
    ("web-04-card-desk",    "03-网页版-谋略卡选项.png",      1280),
    ("web-05-rain-desk",    "04-网页版-雨夜.png",           1280),
    ("web-06-wave-desk",    "05-网页版-风浪回合.png",        1280),
    ("web-07-gallery-desk", "06-网页版-结局图鉴.png",        1280),
    ("web-08-panel-desk",   "07-网页版-人物好感.png",        1280),
    ("web-09-ending-desk",  "08-网页版-结局.png",           1280),
    ("web-11-era-desk",     "09-网页版-时代过场.png",        1280),
    ("pwa-01-title-iphone", "10-安卓-标题.png",             680),
    ("pwa-03-choice-iphone","11-安卓-对话与抉择.png",        680),
    ("pwa-10-drag-iphone",  "12-安卓-长按拖拽选择.png",      680),
    ("pwa-06-wave-iphone",  "13-安卓-风浪回合.png",          680),
    ("pwa-08-panel-iphone", "14-安卓-人物好感.png",          680),
    ("pwa-09-ending-iphone","15-安卓-结局.png",             680),
    ("pwa-11-era-iphone",   "16-安卓-时代过场.png",          680),
]


def main():
    os.makedirs(OLD, exist_ok=True)
    os.makedirs(DST, exist_ok=True)

    # 旧截图先移到 _build/old，不留在发布目录
    moved = 0
    for f in glob.glob(os.path.join(DST, "*.png")):
        target = os.path.join(OLD, os.path.basename(f))
        if os.path.exists(target):
            os.remove(target)
        shutil.move(f, target)
        moved += 1
    print(f"[截图] 旧图移至 _build/old: {moved} 张")

    n = 0
    for src, dst_name, width in SHOT_MAP:
        p = os.path.join(SHOTS, src + ".png")
        if not os.path.exists(p):
            print("  !! 缺图:", src)
            continue
        im = Image.open(p).convert("RGB")
        h = round(width * im.size[1] / im.size[0])
        im = im.resize((width, h), Image.LANCZOS)
        out = os.path.join(DST, dst_name)
        im.save(out, "PNG", optimize=True)
        n += 1
    print(f"[截图] 生成新图 {n} 张 -> {DST}")

    # 旧目录/旧产物清理
    for name in ["01-网页版（吉卜力风格）", "02-安卓版PWA（液态玻璃）"]:
        p = os.path.join(ROOT, name)
        if os.path.isdir(p):
            t = os.path.join(OLD, name)
            if os.path.isdir(t):
                shutil.rmtree(t)
            shutil.move(p, t)
            print(f"[目录] 旧版移至 _build/old: {name}")

    for name in ["风起旧厂街-v2.4-三端发布包.zip"]:
        p = os.path.join(ROOT, name)
        if os.path.isfile(p):
            shutil.move(p, os.path.join(OLD, name))

    old_apk = os.path.join(ROOT, "03-Android安装包", "风起旧厂街-v2.4.apk")
    if os.path.isfile(old_apk):
        shutil.move(old_apk, os.path.join(OLD, "风起旧厂街-v2.4.apk"))
        print("[APK] 旧包移至 _build/old")


if __name__ == "__main__":
    main()

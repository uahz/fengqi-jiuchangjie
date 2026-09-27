#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""打包发布 zip：风起旧厂街-v2.5-全平台发布包.zip

包内结构与 v2.4 保持一致：01~07 目录 + 使用说明.txt + fengqi.ico
（构建脚本 _build/ 与素材源 _art/ 属源码仓库内容，不随发布包分发）
文件名用 UTF-8 编码（带 EFS 标志位），Win10+ 资源管理器 / 7-Zip / Bandizip 均可正确显示。
"""
import os, zipfile

ROOT = "C:/Users/Administrator/WorkBuddy/狂飙game"
ZIP_NAME = "风起旧厂街-v2.5-全平台发布包.zip"
ZIP_PATH = os.path.join(ROOT, ZIP_NAME)

INCLUDE_DIRS = [
    "01-网页版（写实电影感）",
    "02-安卓版PWA（写实电影感）",
    "03-Android安装包",
    "04-Windows桌面版",
    "05-Android源码工程",
    "06-文档",
    "07-截图",
]
INCLUDE_FILES = ["使用说明.txt", "fengqi.ico"]

EXCLUDE_NAMES = {".DS_Store", "Thumbs.db"}


def main():
    if os.path.exists(ZIP_PATH):
        os.remove(ZIP_PATH)
    n = 0
    total = 0
    with zipfile.ZipFile(ZIP_PATH, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for f in INCLUDE_FILES:
            p = os.path.join(ROOT, f)
            z.write(p, f)
            n += 1
            total += os.path.getsize(p)
        for d in INCLUDE_DIRS:
            base = os.path.join(ROOT, d)
            for root, dirs, files in os.walk(base):
                dirs[:] = [x for x in dirs if x not in EXCLUDE_NAMES]
                for f in sorted(files):
                    if f in EXCLUDE_NAMES or f.startswith("_shot_") or f.startswith("_probe_"):
                        continue
                    full = os.path.join(root, f)
                    rel = os.path.relpath(full, ROOT).replace("\\", "/")
                    z.write(full, rel)
                    n += 1
                    total += os.path.getsize(full)

    sz = os.path.getsize(ZIP_PATH)
    print(f"产物: {ZIP_PATH}")
    print(f"文件数: {n}   原始 {total/1024/1024:.1f} MB   压缩后 {sz/1024/1024:.1f} MB")

    # 校验：重新读一遍，确认条目名不乱码、结构完整
    with zipfile.ZipFile(ZIP_PATH) as z:
        bad = z.testzip()
        names = z.namelist()
        print("zip 完整性:", "OK" if bad is None else f"损坏 {bad}")
        print(f"条目数: {len(names)}")
        print("顶层结构:")
        tops = sorted({x.split("/")[0] for x in names})
        for t in tops:
            cnt = sum(1 for x in names if x.split("/")[0] == t)
            print(f"  {t}  ({cnt} 项)")


if __name__ == "__main__":
    main()

#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""构建 Windows 桌面版 EXE（pywebview + PyInstaller onefile）。

PyInstaller 对非 ASCII 路径同样敏感，因此在 %TEMP% 下用纯 ASCII 目录构建，
产物再拷回 04-Windows桌面版/。
"""
import os, shutil, subprocess, sys

ROOT = "C:/Users/Administrator/WorkBuddy/狂飙game"
SRC = os.path.join(ROOT, "_build", "desktop")
PY = "C:/Users/Administrator/.workbuddy/binaries/python/envs/default/Scripts/python.exe"
T = os.environ.get("TEMP", r"C:\Windows\Temp")
WORK = os.path.join(T, "fqdesk")
OUT_DIR = os.path.join(ROOT, "04-Windows桌面版")

# 每个目标文件按优先级在多个位置查找，兼容「工作区布局」与「仓库布局」
FILES = {
    "fengqi_jiuchangjie.py": ["_build/desktop/fengqi_jiuchangjie.py", "fengqi_jiuchangjie.py"],
    "FengqiJiuchangjie.spec": ["_build/desktop/FengqiJiuchangjie.spec", "FengqiJiuchangjie.spec"],
    "fengqi.ico": ["_build/desktop/fengqi.ico", "fengqi.ico"],
    "fengqi-jiuchangjie.html": [
        "_build/desktop/fengqi-jiuchangjie.html",
        "01-网页版（写实电影感）/fengqi-jiuchangjie.html",
        "fengqi-jiuchangjie.html",
    ],
}


def resolve(name):
    for rel in FILES[name]:
        p = os.path.join(ROOT, rel.replace("/", os.sep))
        if os.path.isfile(p):
            return p
    raise SystemExit(f"找不到 {name}，候选位置：{FILES[name]}")


def main():
    if os.path.isdir(WORK):
        shutil.rmtree(WORK)
    os.makedirs(WORK)
    for f in FILES:
        shutil.copy2(resolve(f), os.path.join(WORK, f))
        print(f"    取材 {f}  <- {os.path.relpath(resolve(f), ROOT)}")

    print("[1/2] PyInstaller 打包（约 1-3 分钟）")
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    r = subprocess.run(
        [PY, "-m", "PyInstaller", "--clean", "--noconfirm", "FengqiJiuchangjie.spec"],
        cwd=WORK, capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)
    tail = (r.stdout or "")[-1800:]
    if r.returncode != 0:
        print(tail)
        print((r.stderr or "")[-1800:])
        raise SystemExit("[FAIL] PyInstaller 打包失败")

    exe = os.path.join(WORK, "dist", "FengqiJiuchangjie.exe")
    if not os.path.exists(exe):
        raise SystemExit("[FAIL] 未生成 EXE")

    print("[2/2] 自检 + 输出")
    sr = subprocess.run([exe, "--selftest"], capture_output=True, text=True,
                        encoding="utf-8", errors="replace", timeout=120)
    print("     " + (sr.stdout or sr.stderr or "").strip()[:400])

    os.makedirs(OUT_DIR, exist_ok=True)
    dst = os.path.join(OUT_DIR, "FengqiJiuchangjie.exe")
    shutil.copy2(exe, dst)
    sz = os.path.getsize(dst) / 1024 / 1024
    print(f"     产物: {dst}  ({sz:.1f} MB)")


if __name__ == "__main__":
    main()

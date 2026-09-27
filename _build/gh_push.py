#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""把 v2.5 同步到 GitHub（uahz/fengqi-jiuchangjie）。

本沙箱里 git 协议到 github.com 不通（CONNECT tunnel 502），但 api.github.com 可用，
因此走 Git Data API：blob -> tree(base_tree) -> commit -> 更新 ref，一次提交原子完成，
删除文件用 tree 里 sha=null 表达。

用法：python _build/gh_push.py [--dry]
"""
import os, sys, json, base64, subprocess, tempfile, glob

ROOT = "C:/Users/Administrator/WorkBuddy/狂飙game"
GH = r"C:\Program Files\GitHub CLI\gh.exe"
OWNER, REPO = "uahz", "fengqi-jiuchangjie"
BRANCH = "main"
TMP = os.path.join(os.environ.get("TEMP", r"C:\Windows\Temp"), "ghpush")
MESSAGE = """v2.5: 写实电影感全平台改版 + 安卓性能优化 + 全平台长按拖拽

画风
- 7 个场景背景全部换为照片级写实图像（暗夜低照度、暖琥珀实用光 vs 冷青阴影、
  浅景深、湿面反光），横向 1440w / 竖向 880w 两套构图
- 三端 UI 统一为暗夜玻璃拟态 + 暖金强调色（弃用旧「网页吉卜力 / 安卓液态玻璃」双风格）
- Q 版立绘改为虚化前景剪影（brightness(0) + blur(20px)），不暴露卡通造型
- 新图标：暗底暖金鲤鱼（旧厂街鱼摊意象），32px 下仍可辨识

性能
- 背景由 base64 内联改为独立 WebP 按需加载：页面 1020 KB -> 121 KB
- APK 1065 KB -> 813 KB（剔除 APK 用不到的 PWA 图标与 manifest）
- WebView 关闭系统强制暗色（保护照片调色）、开启 setOffscreenPreRaster 预栅格化
- 移除重复元素的 backdrop-filter，弱机自动进入低特效档
- assets 中 .webp 以 store 方式存入，可 mmap 直接读取
- 注入 --sat / --sab 安全区变量，顶栏不再被状态栏/刘海遮挡

交互
- 长按拖拽选择从 PWA 分支并入共用增强层，网页 / 桌面 / 安卓三端一致
- 新增底部悬浮导航（窄屏/触屏显示）

修复
- 桌面版原先以 about:blank 加载，localStorage 不可用 -> 存档实际失效；
  改为本地 HTTP 服务承载正常 origin，--selftest 已验证可读写

验证
- __qa(600) × 三端：1800 局全部到达结局、0 错误
- 长按拖拽 7 项真机模拟断言全通过（Playwright 真实指针事件序列）
- 覆盖 1440/1920 桌面与 390/412/360 小屏

版本：com.uahz.fengqi versionCode 25 / versionName 2.5（签名不变，可覆盖安装）"""

# ---------------------------------------------------------------- 文件映射
def build_manifest():
    m = {}

    def add(local, repo):
        p = os.path.join(ROOT, local.replace("/", os.sep))
        if not os.path.isfile(p):
            raise SystemExit("缺文件: " + local)
        m[repo] = p

    # 主产物
    add("01-网页版（写实电影感）/fengqi-jiuchangjie.html", "fengqi-jiuchangjie.html")
    add("fengqi.ico", "fengqi.ico")

    # PWA
    for f in ("index.html", "manifest.json", "sw.js", "icon-192.png", "icon-512.png"):
        add(f"02-安卓版PWA（写实电影感）/{f}", f"mobile/{f}")
    for p in sorted(glob.glob(os.path.join(ROOT, "02-安卓版PWA（写实电影感）", "img", "*.webp"))):
        m["mobile/img/" + os.path.basename(p)] = p

    # Android 工程
    androot = os.path.join(ROOT, "05-Android源码工程")
    for r, _, fs in os.walk(androot):
        for f in sorted(fs):
            full = os.path.join(r, f)
            rel = os.path.relpath(full, androot).replace("\\", "/")
            m["android/" + rel] = full

    # 截图
    for p in sorted(glob.glob(os.path.join(ROOT, "07-截图", "*.png"))):
        m["_shots/" + os.path.basename(p)] = p

    # 文档
    add("06-文档/fengqi-jiuchangjie-design.md", "fengqi-jiuchangjie-design.md")
    add("_build/repo-readme.md", "README.md")

    # 桌面版构建源
    add("_build/desktop/fengqi_jiuchangjie.py", "fengqi_jiuchangjie.py")
    add("_build/desktop/FengqiJiuchangjie.spec", "FengqiJiuchangjie.spec")

    # 构建脚本 + 母版
    for f in sorted(os.listdir(os.path.join(ROOT, "_build"))):
        p = os.path.join(ROOT, "_build", f)
        if os.path.isfile(p) and f.split(".")[-1] in ("py", "css", "js", "md"):
            if f == "repo-readme.md":
                continue
            m["_build/" + f] = p
    add("_build/base/fengqi-jiuchangjie.html", "_build/base/fengqi-jiuchangjie.html")

    # 构建素材（背景 + 图标）
    for sub in ("land", "port", "icons", "mipmap"):
        base = os.path.join(ROOT, "_art", "out", sub)
        for r, _, fs in os.walk(base):
            for f in sorted(fs):
                full = os.path.join(r, f)
                rel = os.path.relpath(full, os.path.join(ROOT, "_art", "out")).replace("\\", "/")
                m["_art/out/" + rel] = full
    return m


# 需要从仓库删除的旧文件
DELETE = [
    ".write-probe",   # 写权限探针，随本次提交一并清掉
    "_shots/gao-1-title.png", "_shots/gao-2-ch1.png", "_shots/gao-3-choice.png",
    "_shots/gao-4-era.png", "_shots/gao-5-ch2.png", "_shots/gao-6-ending.png",
    "_shots/gao-7-gallery.png", "_shots/gao-8-wave.png", "_shots/gao-9-card.png",
    "_shots/gao-10-aff.png", "_shots/gao-11-ach.png", "_shots/gao-a-1-title.png",
    "_shots/gao-a-2-dialog.png", "_shots/gao-a-3-choice.png", "_shots/gao-a-4-panel.png",
    "_shots/gao-a-drag.png",
    "android/assets/icon-192.png", "android/assets/icon-512.png", "android/assets/manifest.json",
    "android/build_apk.bat",   # 会被新版覆盖，此处仅示意；实际由 manifest 覆盖
]


def api(method, endpoint, body=None, raw_file=None):
    cmd = [GH, "api", endpoint, "-X", method]
    tmp = None
    if body is not None:
        os.makedirs(TMP, exist_ok=True)
        tmp = os.path.join(TMP, "body.json")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(body, f)
        cmd += ["--input", tmp]
    if raw_file:
        cmd += ["--input", raw_file]
    env = child_env()
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", env=env)
    if r.returncode != 0:
        if tmp and os.path.exists(tmp):
            os.remove(tmp)
        return None, (r.stdout or "") + (r.stderr or "")
    if tmp and os.path.exists(tmp):
        os.remove(tmp)
    out = r.stdout.strip()
    try:
        return json.loads(out) if out else {}, ""
    except Exception:
        return {"_raw": out}, ""


def child_env():
    """把 PUSH_TOKEN 提升为 GH_TOKEN（gh 的优先级：GH_TOKEN > GITHUB_TOKEN），
    token 只存在于进程环境里，不落盘。"""
    env = dict(os.environ)
    t = os.environ.get("PUSH_TOKEN") or os.environ.get("GH_PUSH_TOKEN")
    if t:
        env.pop("GITHUB_TOKEN", None)
        env["GH_TOKEN"] = t
    return env


def main():
    dry = "--dry" in sys.argv
    files = build_manifest()
    print(f"待上传文件: {len(files)} 个，合计 {sum(os.path.getsize(p) for p in files.values())/1024/1024:.1f} MB")
    if dry:
        for k in sorted(files)[:12]:
            print("   ", k)
        print("    ...")
        return

    # 1) 当前 ref / commit / tree
    ref, err = api("GET", f"repos/{OWNER}/{REPO}/git/ref/heads/{BRANCH}")
    if not ref:
        raise SystemExit("取 ref 失败: " + err)
    head_sha = ref["object"]["sha"]
    commit, err = api("GET", f"repos/{OWNER}/{REPO}/git/commits/{head_sha}")
    base_tree = commit["tree"]["sha"]
    print(f"当前 HEAD {head_sha[:8]}  tree {base_tree[:8]}")

    # 2) 逐个建 blob
    entries = []
    for i, (repo_path, local) in enumerate(sorted(files.items()), 1):
        with open(local, "rb") as f:
            content = base64.b64encode(f.read()).decode()
        blob, err = api("POST", f"repos/{OWNER}/{REPO}/git/blobs",
                        {"content": content, "encoding": "base64"})
        if not blob or "sha" not in blob:
            raise SystemExit(f"blob 失败 {repo_path}: {err[:300]}")
        entries.append({"path": repo_path, "mode": "100644", "type": "blob", "sha": blob["sha"]})
        if i % 10 == 0 or i == len(files):
            print(f"  blob {i}/{len(files)}")

    # 3) 删除项
    existing, _ = api("GET", f"repos/{OWNER}/{REPO}/git/trees/{base_tree}?recursive=1")
    have = {t["path"] for t in existing.get("tree", [])} if existing else set()
    dels = [p for p in DELETE if p in have and p not in files]
    for p in dels:
        entries.append({"path": p, "mode": "100644", "type": "blob", "sha": None})
    print(f"删除旧文件: {len(dels)} 个")

    # 4) tree -> commit -> ref
    tree, err = api("POST", f"repos/{OWNER}/{REPO}/git/trees",
                    {"base_tree": base_tree, "tree": entries})
    if not tree or "sha" not in tree:
        raise SystemExit("建 tree 失败: " + err[:400])
    newc, err = api("POST", f"repos/{OWNER}/{REPO}/git/commits",
                    {"message": MESSAGE, "tree": tree["sha"], "parents": [head_sha]})
    if not newc or "sha" not in newc:
        raise SystemExit("建 commit 失败: " + err[:400])
    upd, err = api("PATCH", f"repos/{OWNER}/{REPO}/git/refs/heads/{BRANCH}",
                   {"sha": newc["sha"], "force": False})
    if not upd:
        raise SystemExit("更新 ref 失败: " + err[:400])
    print(f"\n提交成功: {newc['sha'][:8]}  https://github.com/{OWNER}/{REPO}/commit/{newc['sha']}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""创建 GitHub Release v2.5 并上传 APK / EXE 资产。

资产走 uploads.github.com（该域在本沙箱可达），二进制不进仓库。
"""
import os, sys, json, subprocess

ROOT = "C:/Users/Administrator/WorkBuddy/狂飙game"
GH = r"C:\Program Files\GitHub CLI\gh.exe"
OWNER, REPO = "uahz", "fengqi-jiuchangjie"
TAG = "v2.5"
TMP = os.path.join(os.environ.get("TEMP", r"C:\Windows\Temp"), "ghrel")

NAME = "风起旧厂街 V2.5 · 写实电影感 + 全平台长按拖拽 + 安卓性能优化"

BODY = """## 📦 V2.5 全平台发布

### 🎬 画风整体改成「写实电影感」
- 7 个场景背景**全部换成照片级写实图像**：旧厂街鱼市 / 派出所走廊 / 白金瀚 / 大厦顶层 / 雨夜街道 / 审讯室 / 晨光天台
- 低照度暗夜基调 · 暖琥珀实用光 × 冷青阴影对撞 · 浅景深 · 胶片颗粒 · 湿面反光
- 三端 UI 统一为**暗夜玻璃拟态 + 暖金强调色**（弃用旧的「网页吉卜力奶油色 / 安卓液态玻璃」双风格）
- 对话场景不再使用 Q 版卡通立绘，改为**虚化前景剪影**暗示在场，角色辨识交给说话人铭牌

### 🎨 全新图标
- 暗底暖金鲤鱼（取自主角起点的鱼摊意象），三端统一；**缩到 32px 仍清晰可辨**

### ⚡ 安卓性能优化
| 指标 | 优化前 | 优化后 |
|---|---|---|
| APK 体积 | 1065 KB | **813 KB** |
| 页面 HTML | 1020 KB | **121 KB** |

- 背景由 base64 内联改为**独立 WebP 文件按需加载**，首屏解析开销大幅下降
- **关闭系统强制暗色**（`setAlgorithmicDarkeningAllowed(false)` / `FORCE_DARK_OFF`）——否则 Android 10+ 会自动反色页面，把写实照片的调色毁掉
- 开启 `setOffscreenPreRaster` 预栅格化，滑动更稳
- 移除重复元素（选项卡 / 图鉴格 / 成就卡）的 `backdrop-filter`，只在对白框等关键元素保留毛玻璃
- **弱机自动低特效档**：`hardwareConcurrency ≤ 4` 时关闭毛玻璃 / 颗粒动画 / Ken Burns 位移
- assets 中的 `.webp` 以不压缩方式存入，可被 `AssetManager` 直接 mmap 读取
- 注入 `--sat` / `--sab` 安全区变量，顶栏不再被状态栏 / 刘海遮挡
- 新增**底部悬浮导航**（状态 / 谋略 / 图鉴），手机拇指可达

### 📱 长按拖拽选择 · 全平台
- 长按选项约 0.17 秒进入拖拽态（含触感反馈），拖动时目标项高亮，松手即选中 —— Apple 式手感
- V2.4 此交互只在安卓 PWA 分支，V2.5 并入共用增强层，**网页 / Windows / 安卓三端一致**

### 🐛 修复
- **桌面版存档失效**：原以 `about:blank` 加载页面，`localStorage` 不可用 —— 存档 / 图鉴 / 成就实际都存不下来。改为经本地 HTTP 服务承载以取得正规 origin，`--selftest` 已实测可读写。

### ✅ 验证
- `window.__qa(600)` × 三端：**1800 局随机通关 100% 到达结局、0 错误**
- 长按拖拽 **7 项真机模拟断言全通过**（Playwright 真实指针事件序列）
- APK 经 `apksigner verify`（v1 + v2 + v3 签名方案全部通过）+ `aapt2 dump badging` 校验
- 覆盖 1440 / 1920 宽桌面与 390 / 412 / 360 小屏视口

### ⬇️ 下载
| 平台 | 文件 |
|---|---|
| **Android** | `fengqi-jiuchangjie-v2.5.apk`（约 0.8 MB，直接安装） |
| **Windows** | `FengqiJiuchangjie.exe`（约 15 MB，免安装） |
| 网页 / PWA | 访问下方 Pages 链接，无需下载 |

> APK 包名 `com.uahz.fengqi` · versionCode 25 · 最低 Android 5.0 · 竖屏
> 签名与 v2.4 一致，可直接覆盖安装（上架应用商店需另换正式签名）

### 🌐 在线试玩
- 网页版：https://uahz.github.io/fengqi-jiuchangjie/fengqi-jiuchangjie.html
- 安卓 PWA：https://uahz.github.io/fengqi-jiuchangjie/mobile/

MIT License · 基于《狂飙》前期故事的同人演绎，暴力情节全部侧写，结局传达「法网恢恢、回头是岸」。"""

ASSETS = [
    ("03-Android安装包/风起旧厂街-v2.5.apk", "fengqi-jiuchangjie-v2.5.apk"),
    ("04-Windows桌面版/FengqiJiuchangjie.exe", "FengqiJiuchangjie.exe"),
    ("风起旧厂街-v2.5-全平台发布包.zip", "fengqi-jiuchangjie-v2.5-full-package.zip"),
]


def child_env():
    """把 PUSH_TOKEN 提升为 GH_TOKEN（gh 优先级：GH_TOKEN > GITHUB_TOKEN），不落盘。"""
    env = dict(os.environ)
    t = os.environ.get("PUSH_TOKEN") or os.environ.get("GH_PUSH_TOKEN")
    if t:
        env.pop("GITHUB_TOKEN", None)
        env["GH_TOKEN"] = t
    return env


def api(method, endpoint, body=None, raw=None, headers=None):
    cmd = [GH, "api", endpoint, "-X", method]
    tmp = None
    if body is not None:
        os.makedirs(TMP, exist_ok=True)
        tmp = os.path.join(TMP, "body.json")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(body, f, ensure_ascii=False)
        cmd += ["--input", tmp]
    if raw:
        cmd += ["--input", raw]
    for h in (headers or []):
        cmd += ["-H", h]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", env=child_env())
    if tmp and os.path.exists(tmp):
        os.remove(tmp)
    out = (r.stdout or "") + (r.stderr or "")
    try:
        return json.loads(r.stdout.strip()) if r.stdout.strip() else {}, out
    except Exception:
        return None, out


def main():
    # 已存在则直接取
    rel, err = api("GET", f"repos/{OWNER}/{REPO}/releases/tags/{TAG}")
    if rel and rel.get("id"):
        print(f"Release {TAG} 已存在，id={rel['id']}")
    else:
        rel, err = api("POST", f"repos/{OWNER}/{REPO}/releases", {
            "tag_name": TAG, "target_commitish": "main",
            "name": NAME, "body": BODY, "draft": False, "prerelease": False,
        })
        if not rel or not rel.get("id"):
            raise SystemExit("创建 Release 失败: " + err[-600:])
        print(f"Release {TAG} 已创建，id={rel['id']}")

    rel_id = rel["id"]
    have = {a["name"] for a in rel.get("assets", [])}
    for rel_path, asset_name in ASSETS:
        p = os.path.join(ROOT, rel_path.replace("/", os.sep))
        if not os.path.exists(p):
            print(f"  !! 缺文件，跳过: {rel_path}")
            continue
        if asset_name in have:
            print(f"  已存在，跳过: {asset_name}")
            continue
        size = os.path.getsize(p)
        print(f"  上传 {asset_name}  {size/1024/1024:.1f} MB ...")
        res, out = api("POST",
                       f"https://uploads.github.com/repos/{OWNER}/{REPO}/releases/{rel_id}/assets?name={asset_name}",
                       raw=p, headers=["Content-Type: application/octet-stream"])
        if res and res.get("id"):
            print(f"    OK  {res['size']} bytes")
        else:
            print(f"    失败: {out[-400:]}")

    # 复查
    rel, _ = api("GET", f"repos/{OWNER}/{REPO}/releases/tags/{TAG}")
    print(f"\nRelease: {rel.get('html_url')}")
    for a in rel.get("assets", []):
        print(f"  {a['name']}  {a['size']/1024/1024:.2f} MB  {a['browser_download_url']}")


if __name__ == "__main__":
    main()

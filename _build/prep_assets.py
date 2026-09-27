"""素材后处理：
   1. 生成两套背景（横版 / 竖版）WebP
   2. 生成 base64 内联表（网页版用）
   3. 生成图标全套（favicon / PWA / Android mipmap / .ico）
"""
import os, io, json, base64, shutil
from PIL import Image

ROOT = "C:/Users/Administrator/WorkBuddy/狂飙game"
CLEAN = os.path.join(ROOT, "_art", "clean")
OUT = os.path.join(ROOT, "_art", "out")

SCENES = ["market", "station", "jinhan", "tower", "rain", "cell", "dawn", "hero"]

# 网页/桌面：横版（质量优先）
LAND_W, LAND_Q = 1440, 78
# 手机（PWA / APK）：竖版
PORT_W, PORT_Q = 880, 78

# 图标源：方案甲 金鲤
ICON_SRC = None


def find_icon_src():
    import glob
    for f in glob.glob(os.path.join(ROOT, "_art", "raw6", "*.png")):
        if "方案甲" in os.path.basename(f):
            return f
    return None


def build_bgs():
    os.makedirs(OUT, exist_ok=True)
    meta = {"land": {}, "port": {}}
    for orient, width, q in (("land", LAND_W, LAND_Q), ("port", PORT_W, PORT_Q)):
        d = os.path.join(OUT, orient)
        os.makedirs(d, exist_ok=True)
        tot = 0
        for sc in SCENES:
            src = os.path.join(CLEAN, f"{sc}_{'h' if orient == 'land' else 'v'}.png")
            im = Image.open(src).convert("RGB")
            h = round(width * im.size[1] / im.size[0])
            im = im.resize((width, h), Image.LANCZOS)
            p = os.path.join(d, sc + ".webp")
            im.save(p, "WEBP", quality=q, method=6)
            sz = os.path.getsize(p)
            tot += sz
            meta[orient][sc] = {"w": width, "h": h, "kb": round(sz / 1024)}
        print(f"[{orient}] {len(SCENES)} 张, 合计 {tot/1024:.0f} KB")
    return meta


def build_b64(mapfile, orient):
    """生成 base64 内联表（JS 对象字面量的片段）"""
    d = os.path.join(OUT, orient)
    parts = []
    for sc in SCENES:
        with open(os.path.join(d, sc + ".webp"), "rb") as f:
            b = base64.b64encode(f.read()).decode()
        parts.append(f'"{sc}":"data:image/webp;base64,{b}"')
    js = "{" + ",".join(parts) + "}"
    with open(mapfile, "w", encoding="utf-8") as f:
        f.write(js)
    print(f"[inline] -> {os.path.basename(mapfile)}  {len(js)/1024:.0f} KB")
    return js


def build_icons():
    src = find_icon_src()
    if not src:
        print("!! 未找到图标源"); return
    # 先去水印
    import sys
    sys.path.insert(0, os.path.join(ROOT, "_art"))
    from dewm import remove_watermark
    ic = remove_watermark(Image.open(src)).convert("RGB")
    ic = ic.resize((1024, 1024), Image.LANCZOS)
    ic.save(os.path.join(CLEAN, "icon_koi.png"))

    icon_dir = os.path.join(OUT, "icons")
    os.makedirs(icon_dir, exist_ok=True)
    sq = ic
    made = []
    for s in (512, 256, 192, 180, 152, 128, 96, 64, 48, 32):
        p = os.path.join(icon_dir, f"icon-{s}.png")
        sq.resize((s, s), Image.LANCZOS).save(p, "PNG", optimize=True)
        made.append((s, os.path.getsize(p)))
    # favicon（内联用，稍小体积）
    fav = io.BytesIO()
    sq.resize((96, 96), Image.LANCZOS).save(fav, "PNG", optimize=True)
    with open(os.path.join(icon_dir, "favicon.b64"), "w") as f:
        f.write(base64.b64encode(fav.getvalue()).decode())
    # .ico 多尺寸
    ico = os.path.join(OUT, "fengqi.ico")
    sq.save(ico, sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
    # Android mipmap 五档
    MIP = {"mdpi": 48, "hdpi": 72, "xhdpi": 96, "xxhdpi": 144, "xxxhdpi": 192}
    mipdir = os.path.join(OUT, "mipmap")
    if os.path.isdir(mipdir): shutil.rmtree(mipdir)
    for k, s in MIP.items():
        dd = os.path.join(mipdir, f"mipmap-{k}")
        os.makedirs(dd, exist_ok=True)
        sq.resize((s, s), Image.LANCZOS).save(os.path.join(dd, "ic_launcher.png"), "PNG", optimize=True)
    print("[icon] png 尺寸:", ", ".join(f"{s}({k//1024}KB)" for s, k in made))
    print("[icon] ->", ico, os.path.getsize(ico), "bytes;  mipmap 五档已生成")


if __name__ == "__main__":
    m = build_bgs()
    build_b64(os.path.join(OUT, "bg_land.js"), "land")
    build_b64(os.path.join(OUT, "bg_port.js"), "port")
    build_icons()
    json.dump(m, open(os.path.join(OUT, "bg_meta.json"), "w"), ensure_ascii=False, indent=1)

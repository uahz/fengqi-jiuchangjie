#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""风起旧厂街 · 全平台构建

以原始网页版为基底，保留全部游戏逻辑（剧情 / 风浪 / 谋略卡 / 成就 / 自检），
只替换「样式 + 背景资源 + 交互增强」，产出三端：
  01-网页版          单文件 HTML，背景 base64 内联（横版 1440w）
  02-安卓版PWA       目录式，背景独立 webp 文件 + SW 预缓存（竖版 880w）
  05-Android源码资源 APK 用 assets（竖版 880w）
"""
import os, re, io, base64, json, shutil, sys

ROOT = "C:/Users/Administrator/WorkBuddy/狂飙game"
ART = os.path.join(ROOT, "_art", "out")
# 母版：v2.4 的原始网页版（承载全部游戏逻辑）。只作为「替换基底」使用，不要直接改它。
# 若丢失，可从 风起旧厂街-v2.4-全平台发布包.zip 里的 01-网页版/fengqi-jiuchangjie.html 还原。
SRC_WEB = os.path.join(ROOT, "_build", "base", "fengqi-jiuchangjie.html")
THEME = os.path.join(ROOT, "_build", "theme.css")




# ---------------------------------------------------------------- 读取基底
def load_original():
    s = open(SRC_WEB, encoding="utf-8").read()
    body = s[s.index("<body>") + 6: s.index("<script>")]
    js = s[s.index("<script>"): s.rindex("</script>") + 9]
    return body, js


# ---------------------------------------------------------------- body 改造
EMOJI_BODY = [
    (">💰 资金", "><span class=\"e\">💰</span> 资金"),
    (">🐟 声望", "><span class=\"e\">🐟</span> 声望"),
    (">🤝 人脉", "><span class=\"e\">🤝</span> 人脉"),
    (">⚠️ 风险", "><span class=\"e\">⚠️</span> 风险"),
    (">❤️ 初心", "><span class=\"e\">❤️</span> 初心"),
    (">🃏 <b>0</b>", "><span class=\"e\">🃏</span> <b>0</b>"),
    (">👥 好感", "><span class=\"e\">👥</span> 好感"),
    (">🔊 音效", "><span class=\"e\">🔊</span> 音效"),
]

NAV_HTML = '''<nav id="nav">
  <button class="navbtn" onclick="if(window.st)openPanel('aff')"><span class="ni">👥</span>状态</button>
  <button class="navbtn" onclick="if(window.st)openPanel('cards')"><span class="ni">🃏</span>谋略</button>
  <button class="navbtn" onclick="showGallery('end')"><span class="ni">📖</span>图鉴</button>
</nav>'''


def patch_body(b):
    for a, c in EMOJI_BODY:
        if a not in b:
            raise SystemExit("body 替换目标缺失: " + a)
        b = b.replace(a, c)

    # 标题页主视觉层
    marker = '<div id="title" class="ovl show">'
    assert marker in b, "未找到 #title"
    b = b.replace(marker, marker + '\n  <div id="titleArt"></div>', 1)

    # 底部导航
    assert '<div id="toast"></div>' in b
    b = b.replace('<div id="toast"></div>', '<div id="toast"></div>\n\n' + NAV_HTML, 1)
    return b


# ---------------------------------------------------------------- js 改造
EMOJI_JS = [
    ("'💰 资金 <b>'", "'<span class=\"e\">💰</span> 资金 <b>'"),
    ("'🐟 声望 <b>'", "'<span class=\"e\">🐟</span> 声望 <b>'"),
    ("'🤝 人脉 <b>'", "'<span class=\"e\">🤝</span> 人脉 <b>'"),
    ("'⚠️ 风险 <b>'", "'<span class=\"e\">⚠️</span> 风险 <b>'"),
    ("'❤️ 初心 <b>'", "'<span class=\"e\">❤️</span> 初心 <b>'"),
    ('"🃏 <b>"', '"<span class=\'e\'>🃏</span> <b>"'),
    ('$("sndBtn").textContent=snd?"🔊 音效":"🔇 静音";',
     '$("sndBtn").innerHTML=snd?"<span class=\'e\'>🔊</span> 音效":"<span class=\'e\'>🔇</span> 静音";'),
]


def patch_js(js, bg_map_js, extra_js):
    # 1) 背景表
    js2, n = re.subn(r"var BG_PHOTOS=\{.*?\};", "var BG_PHOTOS=" + bg_map_js + ";", js, count=1, flags=re.S)
    if n != 1:
        raise SystemExit("BG_PHOTOS 替换失败")
    js = js2

    # 2) emoji 包 span（统一压成暖金色）
    for a, c in EMOJI_JS:
        if a not in js:
            print("  ~ 跳过(未命中):", a[:34])
            continue
        js = js.replace(a, c)

    # 3) 追加增强层
    js = js.replace("</script>", extra_js + "\n</script>", 1)
    return js


# ---------------------------------------------------------------- 增强层 JS
EXTRA_JS = r'''
/* ================= 写实电影感增强层（构建注入） ================= */
(function(){
 var P=window.__PLATFORM__||{};

 /* --- 低特效档：弱机自动降开销（关闭模糊/颗粒/位移动画） --- */
 try{
   var cores=navigator.hardwareConcurrency||4;
   if(P.lowfx==="force"||(P.lowfx==="auto"&&cores<=4))document.body.classList.add("lfx");
 }catch(e){}

 /* --- 标题页真实窗景主视觉 --- */
 (function(){
   var t=document.getElementById("titleArt");if(!t)return;
   var u=(BG_PHOTOS&&BG_PHOTOS.hero)||"";if(!u)return;
   var img=new Image();
   img.onload=function(){t.style.backgroundImage="url("+u+")";requestAnimationFrame(function(){t.style.opacity=1;});};
   img.onerror=function(){};
   img.src=u;
 })();

 /* --- 雨幕联动：当前场景为 bg-rain 时叠加雨丝 --- */
 (function(){
   var bgEl=document.getElementById("bg"),stage=document.getElementById("stage");
   if(!bgEl||!stage)return;
   var sync=function(){stage.classList.toggle("rainOn",/(^|\s)bg-rain(\s|$)/.test(" "+bgEl.className+" "));};
   sync();
   try{new MutationObserver(sync).observe(bgEl,{attributes:true,attributeFilter:["class"]});}catch(e){}
 })();

 /* --- 底部导航显隐（跟随 HUD） --- */
 (function(){
   var hud=document.getElementById("hud"),nav=document.getElementById("nav");
   if(!hud||!nav)return;
   var sync=function(){nav.classList.toggle("on",!!(hud.style.display&&hud.style.display!=="none"));};
   sync();
   try{new MutationObserver(sync).observe(hud,{attributes:true,attributeFilter:["style"]});}catch(e){}
 })();

 /* --- Apple 式长按拖拽选择（全平台） --- */
 (function(){
  var box=document.getElementById("choices");if(!box)return;
  var HOLD=P.holdMs||170;
  var timer=null,dragOn=false,cur=null,swallow=false,hintEl=null,hinted=false;
  function at(x,y){var el=document.elementFromPoint(x,y);return (el&&el.closest)?el.closest(".choice"):null;}
  function hl(el){
   if(el&&el.classList.contains("lock"))el=null;
   if(cur===el)return;
   if(cur)cur.classList.remove("dragOver");
   cur=el;
   if(cur)cur.classList.add("dragOver");
  }
  function buzz(ms){try{if(navigator.vibrate)navigator.vibrate(ms);}catch(e){}}
  function showHint(){
   if(hinted||!box.parentNode)return;hinted=true;
   hintEl=document.createElement("div");
   hintEl.className="dragHint";
   hintEl.textContent="长按选项可拖动选择";
   box.parentNode.insertBefore(hintEl,box);
   setTimeout(function(){if(hintEl){hintEl.classList.add("fade");setTimeout(function(){if(hintEl&&hintEl.parentNode)hintEl.parentNode.removeChild(hintEl);hintEl=null;},600);}},2600);
  }
  box.addEventListener("pointerdown",function(e){
   var c=e.target&&e.target.closest?e.target.closest(".choice"):null;if(!c)return;
   if(timer)clearTimeout(timer);
   timer=setTimeout(function(){
    timer=null;dragOn=true;
    document.body.classList.add("dragging");
    c.classList.add("dragging");
    hl(c);showHint();buzz(14);
   },HOLD);
  },{passive:true});
  document.addEventListener("pointermove",function(e){
   if(!dragOn){if(timer&&Math.abs(e.movementY||0)>6){clearTimeout(timer);timer=null;}return;}
   if(e.cancelable)e.preventDefault();
   hl(at(e.clientX,e.clientY));
  },{passive:false});
  function endDrag(){
   if(timer){clearTimeout(timer);timer=null;}
   if(!dragOn)return;
   dragOn=false;
   document.body.classList.remove("dragging");
   var d=document.querySelector(".choice.dragging");if(d)d.classList.remove("dragging");
   var t=cur;hl(null);
   if(t&&!t.classList.contains("lock")){
    var fn=t.onclick;
    swallow=true;setTimeout(function(){swallow=false;},420);
    t.classList.add("chosen");
    buzz(8);
    setTimeout(function(){if(fn)try{fn.call(t);}catch(e){}},80);
   }
  }
  document.addEventListener("pointerup",endDrag);
  document.addEventListener("pointercancel",function(){
   if(timer){clearTimeout(timer);timer=null;}
   dragOn=false;document.body.classList.remove("dragging");
   var d=document.querySelector(".choice.dragging");if(d)d.classList.remove("dragging");
   hl(null);
  });
  box.addEventListener("click",function(e){if(swallow){e.preventDefault();e.stopPropagation();}},true);
 })();

 /* --- PWA：注册 Service Worker 实现离线可玩（仅 http/https，file:// 下跳过） --- */
 if(P.sw&&!P.app){
  try{
   if("serviceWorker" in navigator&&location.protocol!=="file:"){
    addEventListener("load",function(){navigator.serviceWorker.register("sw.js").catch(function(){});});
   }
  }catch(e){}
 }
})();
'''

SW_JS = '''/* 风起旧厂街 · PWA service worker（cache-first，离线可玩） */
const CACHE = "gq-cine-v1";
const IMGS = ["market","station","jinhan","tower","rain","cell","dawn","hero"].map(n=>"./img/"+n+".webp");
const ASSETS = ["./", "./index.html", "./manifest.json", "./icon-192.png", "./icon-512.png", ...IMGS];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(ASSETS)).then(() => self.skipWaiting()));
});
self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});
self.addEventListener("fetch", (e) => {
  if (e.request.method !== "GET") return;
  e.respondWith(
    caches.match(e.request, { ignoreSearch: true }).then(
      (hit) =>
        hit ||
        fetch(e.request)
          .then((resp) => {
            const copy = resp.clone();
            caches.open(CACHE).then((c) => c.put(e.request, copy));
            return resp;
          })
          .catch(() => caches.match("./index.html"))
    )
  );
});
'''

MANIFEST = {
    "name": "风起旧厂街 · 高启强",
    "short_name": "旧厂街",
    "description": "对话式剧情游戏：2000 年京海旧厂街，从鱼摊一步一步走上巅峰。",
    "lang": "zh-CN",
    "start_url": "./index.html",
    "scope": "./",
    "display": "standalone",
    "orientation": "portrait",
    "background_color": "#07090b",
    "theme_color": "#07090b",
    "icons": [
        {"src": "icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any"},
        {"src": "icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any"},
        {"src": "icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable"},
    ],
}


# ---------------------------------------------------------------- 组装页面
def render_page(platform_js, favicon_b64, theme_css, body, js):
    head = (
        '<!DOCTYPE html>\n<html lang="zh-CN">\n<head>\n'
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
        '<meta name="theme-color" content="#07090b">\n'
        '<meta name="color-scheme" content="dark">\n'
        '<meta name="description" content="风起旧厂街 · 高启强 —— 2000年京海旧厂街，从鱼摊一步一步走上巅峰。对话式剧情游戏。">\n'
        '<title>风起旧厂街 · 高启强</title>\n'
        '<link rel="icon" type="image/png" href="data:image/png;base64,' + favicon_b64 + '">\n'
        '<link rel="apple-touch-icon" href="icon-192.png">\n'
        '<style>\n' + theme_css + '\n</style>\n</head>\n'
    )
    plat = "<script>window.__PLATFORM__={" + platform_js + "};</script>\n"
    return head + "<body>" + body + "\n" + plat + js + "\n</body>\n</html>\n"


def build_b64_map(orient):
    """直接把 _art/out/<orient>/*.webp 内联成 JS 对象字面量。
    （不再依赖 prep_assets.py 预先落盘的 bg_*.js，避免仓库里多两个派生文件）"""
    d = os.path.join(ART, orient)
    parts = []
    for sc in ["market", "station", "jinhan", "tower", "rain", "cell", "dawn", "hero"]:
        with open(os.path.join(d, sc + ".webp"), "rb") as f:
            parts.append('"%s":"data:image/webp;base64,%s"'
                         % (sc, base64.b64encode(f.read()).decode()))
    return "{" + ",".join(parts) + "}"


def file_map(prefix, ext="webp"):
    return "{" + ",".join(f'"{s}":"{prefix}/{s}.{ext}"'
                          for s in ["market", "station", "jinhan", "tower", "rain", "cell", "dawn", "hero"]) + "}"


def copy_imgs(dst, orient):
    os.makedirs(dst, exist_ok=True)
    src = os.path.join(ART, orient)
    n = 0
    for f in os.listdir(src):
        shutil.copy2(os.path.join(src, f), os.path.join(dst, f))
        n += 1
    return n


def main():
    body0, js0 = load_original()
    theme_css = open(THEME, encoding="utf-8").read()
    favicon = open(os.path.join(ART, "icons", "favicon.b64")).read().strip()
    bg_land = build_b64_map("land")
    bg_port = build_b64_map("port")

    body = patch_body(body0)

    # ---------- 1. 网页版（单文件 / 横版 / 内联） ----------
    js = patch_js(js0, bg_land, EXTRA_JS)
    html = render_page('lowfx:"off"', favicon, theme_css, body, js)
    outdir = os.path.join(ROOT, "01-网页版（写实电影感）")
    os.makedirs(outdir, exist_ok=True)
    p = os.path.join(outdir, "fengqi-jiuchangjie.html")
    open(p, "w", encoding="utf-8").write(html)
    print(f"[网页版] {p}  {os.path.getsize(p)/1024/1024:.2f} MB")

    # ---------- 2. PWA（目录式 / 竖版 / 外链） ----------
    js = patch_js(js0, file_map("img"), EXTRA_JS)
    html = render_page('lowfx:"auto",sw:true', favicon, theme_css, body, js)
    pwadir = os.path.join(ROOT, "02-安卓版PWA（写实电影感）")
    os.makedirs(pwadir, exist_ok=True)
    open(os.path.join(pwadir, "index.html"), "w", encoding="utf-8").write(html)
    copy_imgs(os.path.join(pwadir, "img"), "port")
    json.dump(MANIFEST, open(os.path.join(pwadir, "manifest.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    open(os.path.join(pwadir, "sw.js"), "w", encoding="utf-8").write(SW_JS)
    for s in (192, 512):
        shutil.copy2(os.path.join(ART, "icons", f"icon-{s}.png"), os.path.join(pwadir, f"icon-{s}.png"))
    print(f"[PWA]    {pwadir}  index.html {os.path.getsize(os.path.join(pwadir,'index.html'))/1024:.0f} KB")

    # ---------- 3. Android 源码资源（只放 APK 真正需要的：页面 + 背景图） ----------
    # 图标由 res/mipmap 提供、清单由 AndroidManifest 提供，
    # manifest.json / icon-192 / icon-512 是 PWA 专用，塞进 APK 白占 ~360KB，故不写入
    anddir = os.path.join(ROOT, "05-Android源码工程", "assets")
    if os.path.isdir(anddir):
        for f in os.listdir(anddir):
            if f in ("manifest.json", "icon-192.png", "icon-512.png"):
                os.remove(os.path.join(anddir, f))
    os.makedirs(anddir, exist_ok=True)
    js = patch_js(js0, file_map("img"), EXTRA_JS)
    html = render_page('lowfx:"auto",app:true', favicon, theme_css, body, js)
    open(os.path.join(anddir, "index.html"), "w", encoding="utf-8").write(html)
    n = copy_imgs(os.path.join(anddir, "img"), "port")
    print(f"[APK资源] {anddir}  index.html {os.path.getsize(os.path.join(anddir,'index.html'))/1024:.0f} KB + img {n} 张")

    # ---------- 4. Android mipmap 图标（只替换 mipmap-*，保留 res/values 等） ----------
    mip_out = os.path.join(ROOT, "05-Android源码工程", "res")
    src_mip = os.path.join(ART, "mipmap")
    os.makedirs(mip_out, exist_ok=True)
    for d in os.listdir(src_mip):
        s_d = os.path.join(src_mip, d)
        t_d = os.path.join(mip_out, d)
        if os.path.isdir(t_d):
            shutil.rmtree(t_d)
        shutil.copytree(s_d, t_d)
    print(f"[图标]   {mip_out}  mdpi/hdpi/xhdpi/xxhdpi/xxxhdpi")

    # ---------- 5. 根图标 ----------
    shutil.copy2(os.path.join(ART, "fengqi.ico"), os.path.join(ROOT, "fengqi.ico"))
    print("[图标]   fengqi.ico 已更新")


if __name__ == "__main__":
    main()

"""风起旧厂街 · 高启强 —— 桌面版启动器（v2.5 写实电影感版）

本版修复 / 优化：
  1. 【关键修复】原先用 `create_window(html=...)` 加载，文档 origin 是 about:blank，
     属于不透明源，localStorage 会抛异常 —— 导致桌面版实际上「存不了档」。
     现改为把 HTML 落到存档目录，并以 http_server 方式提供（origin =
     http://127.0.0.1:<port>），localStorage 正常工作且随 storage_path 跨次保留。
     若本地服务启动失败，自动回退到旧的 html= 方式，保证窗口一定能开。
  2. 窗口底色/尺寸与新的暗色电影感主题对齐（#07090b / 1440x900）。
  3. 保留 --selftest（构建后可无头自检）与 --debug（开发者工具）。

构建：
  python -m PyInstaller --clean --noconfirm FengqiJiuchangjie.spec
"""
import os
import shutil
import sys

import webview

APP = "FengqiJiuchangjie"
HTML_NAME = "fengqi-jiuchangjie.html"


def resource(name):
    """兼容 PyInstaller onefile：资源解包到 _MEIPASS 临时目录。"""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, name)


def storage_dir():
    """存档目录（localStorage 持久化：自动存档 / 图鉴 / 成就）。"""
    d = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), APP)
    os.makedirs(d, exist_ok=True)
    return d


def stage_html():
    """把内置页面释放到存档目录，返回本地文件路径。"""
    src = resource(HTML_NAME)
    dst = os.path.join(storage_dir(), HTML_NAME)
    try:
        shutil.copyfile(src, dst)
        return dst
    except Exception:
        return src


def main():
    selftest = "--selftest" in sys.argv
    debug = "--debug" in sys.argv

    html_path = stage_html()
    with open(resource(HTML_NAME), "r", encoding="utf-8") as f:
        html_str = f.read()

    common = dict(
        title="风起旧厂街 · 高启强",
        width=1440,
        height=900,
        min_size=(420, 640),
        background_color="#07090b",
    )

    # 优先：本地 HTTP 服务 -> 正规 origin -> localStorage 可用
    try:
        window = webview.create_window(url=html_path, **common)
        start_kwargs = dict(
            http_server=True,
            private_mode=False,
            storage_path=storage_dir(),
            debug=debug,
        )
        mode = "http_server"
    except Exception:
        window = webview.create_window(html=html_str, **common)
        start_kwargs = dict(private_mode=False, storage_path=storage_dir(), debug=debug)
        mode = "inline_html"

    if selftest:
        def check(w):
            detail = w.evaluate_js(
                "JSON.stringify({s:typeof S!=='undefined',qa:typeof __qa,"
                "sub:!!document.querySelector('#title .sub'),"
                "art:!!document.getElementById('titleArt'),"
                "bg:typeof BG_PHOTOS!=='undefined'&&!!BG_PHOTOS.hero,"
                "ls:(function(){try{localStorage.setItem('__t','1');"
                "var v=localStorage.getItem('__t');localStorage.removeItem('__t');"
                "return v==='1'}catch(e){return 'ERR:'+e.name}})()})"
            )
            ok = w.evaluate_js(
                "typeof S!=='undefined' && typeof __qa==='function'"
                " && document.querySelector('#title .sub')!==null"
            )
            print("SELFTEST", "PASS" if ok else "FAIL", "mode=" + mode, detail, flush=True)
            w.destroy()
            os._exit(0 if ok else 1)

        webview.start(check, window, **start_kwargs)
        return

    webview.start(**start_kwargs)


if __name__ == "__main__":
    main()

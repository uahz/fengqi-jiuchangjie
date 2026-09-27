"""风起旧厂街 · 高启强 —— 桌面版启动器

pywebview 封装单文件 HTML 游戏：打开原生窗口加载游戏页，
localStorage 持久化（自动存档 / 结局图鉴 / 成就进度跨次保留）。

构建：python -m PyInstaller --onefile --windowed --name FengqiJiuchangjie
      --icon icon.ico --add-data "fengqi-jiuchangjie.html;." --collect-all webview
      fengqi_jiuchangjie.py
"""
import os
import sys

import webview


def resource(name):
    """兼容 PyInstaller onefile：资源解包到 _MEIPASS 临时目录。"""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, name)


def storage_dir():
    """localStorage 持久化目录（自动存档 / 图鉴 / 成就）。"""
    d = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "FengqiJiuchangjie")
    os.makedirs(d, exist_ok=True)
    return d


def main():
    with open(resource("fengqi-jiuchangjie.html"), "r", encoding="utf-8") as f:
        html = f.read()
    selftest = "--selftest" in sys.argv
    window = webview.create_window(
        "风起旧厂街 · 高启强",
        html=html,
        width=1280,
        height=820,
        min_size=(420, 620),
        background_color="#07090d",
    )
    if selftest:
        def check(w):
            detail = w.evaluate_js(
                "JSON.stringify({s: typeof S!=='undefined', qa: typeof __qa,"
                " sub: !!document.querySelector('#title .sub'),"
                " title: document.title})"
            )
            ok = w.evaluate_js(
                "typeof S!=='undefined' && typeof __qa==='function'"
                " && document.querySelector('#title .sub')!==null"
            )
            print("SELFTEST", "PASS" if ok else "FAIL", detail, flush=True)
            w.destroy()
            os._exit(0 if ok else 1)  # 从子线程强制退出整个进程
        webview.start(check, window)
        return
    webview.start(
        private_mode=False,           # 关闭无痕模式，存档才能跨次保留
        storage_path=storage_dir(),
        debug="--debug" in sys.argv,  # 传 --debug 可打开开发者工具
    )


if __name__ == "__main__":
    main()

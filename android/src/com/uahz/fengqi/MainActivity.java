package com.uahz.fengqi;

import android.annotation.SuppressLint;
import android.app.Activity;
import android.graphics.Color;
import android.os.Build;
import android.os.Bundle;
import android.view.View;
import android.view.ViewGroup;
import android.view.Window;
import android.view.WindowInsets;
import android.view.WindowInsetsController;
import android.view.WindowManager;
import android.webkit.JavascriptInterface;
import android.webkit.WebChromeClient;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;

/**
 * 风起旧厂街 · 高启强 —— 原生安卓外壳
 *
 * 关键能力：
 *  1. 沉浸式状态栏/导航栏：全透明 + 边到边，把系统栏高度通过 JS 桥接给页面做安全区留白
 *  2. 返回键分层处理：先让页面关闭弹层（图鉴/面板/风浪），页面没处理才退出应用
 *  3. 主题联动：页面的日/夜模式可控制状态栏图标深浅（深色图标 / 浅色图标）
 *  4. DOM Storage：存档、成就、图鉴持久化
 */
public class MainActivity extends Activity {

    private WebView web;
    private int insetTop = 0;
    private int insetBottom = 0;
    private boolean dayMode = false;

    public class Bridge {
        /** 页面切换日/夜主题时调用，用于切换状态栏图标深浅 */
        @JavascriptInterface
        public void setTheme(final String mode) {
            dayMode = "day".equals(mode);
            runOnUiThread(new Runnable() {
                public void run() { applyBarIcons(); }
            });
        }

        /** 页面请求退出应用 */
        @JavascriptInterface
        public void exitApp() {
            runOnUiThread(new Runnable() {
                public void run() { finish(); }
            });
        }

        /** 返回系统栏内边距（CSS 像素），页面可随时查询 */
        @JavascriptInterface
        public String insets() {
            float d = getResources().getDisplayMetrics().density;
            return "{\"top\":" + (int) (insetTop / d) + ",\"bottom\":" + (int) (insetBottom / d) + "}";
        }
    }

    @SuppressLint({"SetJavaScriptEnabled", "AddJavascriptInterface"})
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        Window w = getWindow();
        // 边到边：系统栏全透明，内容可延伸至状态栏/导航栏之下
        w.addFlags(WindowManager.LayoutParams.FLAG_DRAWS_SYSTEM_BAR_BACKGROUNDS);
        w.setStatusBarColor(Color.TRANSPARENT);
        w.setNavigationBarColor(Color.TRANSPARENT);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
            w.getAttributes().layoutInDisplayCutoutMode =
                    WindowManager.LayoutParams.LAYOUT_IN_DISPLAY_CUTOUT_MODE_SHORT_EDGES;
            w.setAttributes(w.getAttributes());
        }
        if (Build.VERSION.SDK_INT >= 30) {
            w.setDecorFitsSystemWindows(false);
        } else {
            w.addFlags(WindowManager.LayoutParams.FLAG_LAYOUT_NO_LIMITS);
        }

        web = new WebView(this);
        web.setLayoutParams(new ViewGroup.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT));
        web.setBackgroundColor(0xFF0B0B0F);

        WebSettings s = web.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setDatabaseEnabled(true);
        s.setAllowFileAccess(true);
        s.setAllowContentAccess(true);
        s.setLoadWithOverviewMode(true);
        s.setUseWideViewPort(true);
        s.setSupportZoom(false);
        s.setBuiltInZoomControls(false);
        s.setTextZoom(100);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP) {
            s.setMixedContentMode(WebSettings.MIXED_CONTENT_ALWAYS_ALLOW);
        }

        web.setWebViewClient(new WebViewClient());
        web.setWebChromeClient(new WebChromeClient());
        web.setVerticalScrollBarEnabled(false);
        web.setHorizontalScrollBarEnabled(false);
        web.setOverScrollMode(View.OVER_SCROLL_NEVER);
        web.addJavascriptInterface(new Bridge(), "FQNative");

        // 监听系统栏变化（旋转、手势条切换等），把最新高度同步给页面
        web.setOnApplyWindowInsetsListener(new View.OnApplyWindowInsetsListener() {
            @Override
            public WindowInsets onApplyWindowInsets(View v, WindowInsets insets) {
                insetTop = insets.getSystemWindowInsetTop();
                insetBottom = insets.getSystemWindowInsetBottom();
                pushInsetsToPage();
                return insets;
            }
        });

        setContentView(web);
        web.loadUrl("file:///android_asset/index.html");
    }

    /** 把安全区高度写进 CSS 变量，页面用 var(--sat)/var(--sab) 做留白 */
    private void pushInsetsToPage() {
        if (web == null) return;
        float d = getResources().getDisplayMetrics().density;
        final int top = (int) (insetTop / d);
        final int bottom = (int) (insetBottom / d);
        web.post(new Runnable() {
            public void run() {
                if (web == null) return;
                web.evaluateJavascript(
                        "document.documentElement.style.setProperty('--sat','" + top + "px');"
                      + "document.documentElement.style.setProperty('--sab','" + bottom + "px');"
                      + "window.dispatchEvent(new Event('fq-insets'));", null);
            }
        });
    }

    /** 日间模式用深色状态栏图标，夜间模式用浅色图标 */
    private void applyBarIcons() {
        if (web == null) return;
        if (Build.VERSION.SDK_INT >= 30) {
            WindowInsetsController c = getWindow().getInsetsController();
            if (c != null) {
                c.setSystemBarsAppearance(
                        dayMode ? WindowInsetsController.APPEARANCE_LIGHT_STATUS_BARS : 0,
                        WindowInsetsController.APPEARANCE_LIGHT_STATUS_BARS);
            }
        } else {
            View dv = getWindow().getDecorView();
            int flags = dv.getSystemUiVisibility();
            if (dayMode) flags |= View.SYSTEM_UI_FLAG_LIGHT_STATUS_BAR;
            else flags &= ~View.SYSTEM_UI_FLAG_LIGHT_STATUS_BAR;
            dv.setSystemUiVisibility(flags);
        }
    }

    /**
     * 返回键分层处理：
     * 页面先关掉最上层弹层（图鉴 / 面板 / 风浪回合 / 结局页），
     * 只有页面明确表示"无可关闭的内容"时，才真正退出应用。
     */
    @Override
    public void onBackPressed() {
        if (web == null) { super.onBackPressed(); return; }
        web.evaluateJavascript(
                "(function(){ try { return (window.__fqBack && window.__fqBack()) === true ? 'handled' : 'exit'; }"
              + " catch(e) { return 'exit'; } })()",
                new android.webkit.ValueCallback<String>() {
                    @Override
                    public void onReceiveValue(String value) {
                        if (value == null || !value.contains("handled")) {
                            finish();
                        }
                    }
                });
    }

    @Override
    protected void onDestroy() {
        if (web != null) {
            web.destroy();
            web = null;
        }
        super.onDestroy();
    }
}

package com.uahz.fengqi;

import android.annotation.SuppressLint;
import android.app.Activity;
import android.graphics.Color;
import android.os.Build;
import android.os.Bundle;
import android.view.View;
import android.view.ViewGroup;
import android.view.WindowInsets;
import android.view.WindowManager;
import android.webkit.WebChromeClient;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;

/**
 * 风起旧厂街 · 高启强 —— 原生安卓外壳（v2.5 写实电影感版）
 *
 * 本次针对性优化：
 *  1. 关闭「强制暗色」(AlgorithmicDarkening / ForceDark) —— 否则 Android 10+ 会
 *     自动反色/压暗页面，把精心调色的写实背景照片毁掉，这是画质最关键的一项。
 *  2. 关闭滚动回弹、滚动条、长按选择与过度滚动发光，减少无效重绘。
 *  3. setOffscreenPreRaster —— 滚动时预栅格化，降低滑动掉帧。
 *  4. 背景色与网页主题一致 (#07090B)，配合 windowBackground 消除启动白闪。
 *  5. 把系统状态栏/导航条高度注入 CSS 变量 --sat / --sab，配合 viewport-fit=cover
 *     让 HUD 不被刘海/状态栏遮挡（原先 FLAG_LAYOUT_NO_LIMITS 会直接把顶栏压在状态栏下）。
 *  6. 页面从 index.html 改为相对路径加载 img/*.webp（背景图独立文件，
 *     不再一次性解析 ~1MB base64，首屏解析开销显著下降）。
 */
public class MainActivity extends Activity {

    private static final int BG = 0xFF07090B;
    private WebView web;

    @SuppressLint("SetJavaScriptEnabled")
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        // 沉浸式：内容延伸至状态栏/导航条之下，实际避让交给网页的 --sat/--sab
        getWindow().setFlags(WindowManager.LayoutParams.FLAG_LAYOUT_NO_LIMITS,
                WindowManager.LayoutParams.FLAG_LAYOUT_NO_LIMITS);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP) {
            getWindow().setStatusBarColor(Color.TRANSPARENT);
            getWindow().setNavigationBarColor(Color.TRANSPARENT);
        }
        // 状态栏图标用浅色（深色背景）
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            getWindow().getDecorView().setSystemUiVisibility(
                    View.SYSTEM_UI_FLAG_LAYOUT_STABLE
                            | View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN
                            | View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION);
        }

        web = new WebView(this);
        web.setLayoutParams(new ViewGroup.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT));
        web.setBackgroundColor(BG);

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
        s.setDisplayZoomControls(false);
        s.setMediaPlaybackRequiresUserGesture(false);
        s.setTextZoom(100);
        s.setCacheMode(WebSettings.LOAD_DEFAULT);
        s.setGeolocationEnabled(false);
        s.setSaveFormData(false);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP) {
            s.setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW);
        }
        // ★ 关键：禁止系统强制暗色，保住写实背景照片的原调色
        try {
            if (Build.VERSION.SDK_INT >= 33) {
                s.setAlgorithmicDarkeningAllowed(false);   // API 33+
            } else if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                s.setForceDark(WebSettings.FORCE_DARK_OFF); // API 29-32
            }
        } catch (Throwable ignore) {
        }
        // ★ 预栅格化，滑动更稳（API 23+）
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            try {
                s.setOffscreenPreRaster(true);
            } catch (Throwable ignore) {
            }
        }

        web.setWebViewClient(new WebViewClient() {
            @Override
            public void onPageFinished(WebView v, String url) {
                injectSafeInsets();
            }
        });
        web.setWebChromeClient(new WebChromeClient());
        web.setVerticalScrollBarEnabled(false);
        web.setHorizontalScrollBarEnabled(false);
        web.setOverScrollMode(View.OVER_SCROLL_NEVER);
        web.setLongClickable(false);
        web.setHapticFeedbackEnabled(true);        // 保留 navigator.vibrate / 长按触感
        web.setOnLongClickListener(new View.OnLongClickListener() {   // 禁止系统长按文本选择菜单
            @Override
            public boolean onLongClick(View v) {
                return true;
            }
        });

        setContentView(web);
        web.loadUrl("file:///android_asset/index.html");
    }

    /** 把状态栏 / 导航条高度注入网页 CSS 变量，避免顶栏被刘海或状态栏遮挡 */
    private void injectSafeInsets() {
        if (web == null) return;
        try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
                WindowInsets wi = getWindow().getDecorView().getRootWindowInsets();
                if (wi == null) return;
                int top = wi.getSystemWindowInsetTop();
                int bottom = wi.getSystemWindowInsetBottom();
                final String js = "document.documentElement.style.setProperty('--sat','" + top + "px');"
                        + "document.documentElement.style.setProperty('--sab','" + bottom + "px');"
                        + "document.body && document.body.classList.add('in-app');";
                web.evaluateJavascript(js, null);
            }
        } catch (Throwable ignore) {
        }
    }

    @Override
    protected void onResume() {
        super.onResume();
        if (web != null) {
            web.onResume();
            injectSafeInsets();
        }
    }

    @Override
    protected void onPause() {
        if (web != null) web.onPause();
        super.onPause();
    }

    @Override
    public void onBackPressed() {
        if (web != null && web.canGoBack()) {
            web.goBack();
        } else {
            super.onBackPressed();
        }
    }

    @Override
    protected void onDestroy() {
        if (web != null) {
            web.loadUrl("about:blank");
            web.destroy();
            web = null;
        }
        super.onDestroy();
    }
}

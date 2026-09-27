#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""风起旧厂街 · 安卓 APK 打包（免 Gradle：aapt2 -> javac -> d8 -> zipalign -> apksigner）

要点：
  · aapt2 / apksigner 对「非 ASCII 路径」支持不好，因此先把工程暂存到纯 ASCII
    工作目录再构建，产物最后用 Python 拷回中文目录。
  · 用 zipfile 注入 classes.dex / assets，不依赖 jar。
  · assets 下的 .webp 以「不压缩」存入 —— WebP 已压缩，再压只增加解压耗时；
    store 后 AssetManager 可直接 mmap，首屏与切场景更快。
  · 复用原有 debug 签名，保证新包可覆盖安装旧包。
"""
import os, shutil, subprocess, zipfile

ROOT = "C:/Users/Administrator/WorkBuddy/狂飙game"
PROJ_SRC = os.path.join(ROOT, "05-Android源码工程")
APK_NAME = "风起旧厂街-v2.5.apk"
OUT_DIR = os.path.join(ROOT, "03-Android安装包")

T = os.environ.get("TEMP", r"C:\Windows\Temp")
# 工作目录必须是纯 ASCII —— aapt2 / apksigner 处理不了非 ASCII 路径
# （连 ROOT 里的「狂飙game」都会让 aapt2 报 failed to open directory）
WORK = os.path.join(T, "fqbuild")
STAGE = os.path.join(WORK, "proj")
KEYDIR = os.path.join(WORK, "keystore")

SDK = os.path.join(T, "android-sdk")
JDK = os.path.join(T, "jdk17")
BT = os.path.join(SDK, "build-tools", "34.0.0")
PLAT = os.path.join(SDK, "platforms", "android-34", "android.jar")

AAPT2 = os.path.join(BT, "aapt2.exe")
JAVAC = os.path.join(JDK, "bin", "javac.exe")
JAR = os.path.join(JDK, "bin", "jar.exe")
KEYTOOL = os.path.join(JDK, "bin", "keytool.exe")
D8 = os.path.join(BT, "d8.bat")
ZIPALIGN = os.path.join(BT, "zipalign.exe")
APKSIGNER = os.path.join(BT, "apksigner.bat")


def q(p):
    return '"' + str(p) + '"'


def sh(cmd, label):
    print(f"  -> {label}")
    env = dict(os.environ)
    env["JAVA_HOME"] = JDK          # d8.bat / apksigner.bat 依赖 JAVA_HOME
    env["PATH"] = os.path.join(JDK, "bin") + os.pathsep + env.get("PATH", "")
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", env=env)
    if r.returncode != 0:
        for out in (r.stdout, r.stderr):
            if out:
                print(out[-2500:])
        raise SystemExit(f"[FAIL] {label} (exit {r.returncode})")
    return (r.stdout or "") + (r.stderr or "")


def main():
    for p in (SDK, JDK, AAPT2, JAVAC, JAR, D8, ZIPALIGN, APKSIGNER):
        if not os.path.exists(p):
            raise SystemExit("缺少构建工具: " + p)

    if os.path.isdir(WORK):
        shutil.rmtree(WORK)
    os.makedirs(WORK)
    # 暂存到 ASCII 路径（规避 aapt2 对中文路径的问题）
    shutil.copytree(PROJ_SRC, STAGE)
    for d in ("gen", "classes", "dex"):
        os.makedirs(os.path.join(WORK, d), exist_ok=True)
    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(KEYDIR, exist_ok=True)

    res = os.path.join(STAGE, "res")
    manifest = os.path.join(STAGE, "AndroidManifest.xml")
    assets = os.path.join(STAGE, "assets")
    src = os.path.join(STAGE, "src", "com", "uahz", "fengqi", "MainActivity.java")
    rjava = os.path.join(WORK, "gen", "com", "uahz", "fengqi", "R.java")
    res_zip = os.path.join(WORK, "res.zip")
    base_apk = os.path.join(WORK, "base.apk")
    classes_dir = os.path.join(WORK, "classes")
    classes_jar = os.path.join(WORK, "classes.jar")
    dex_dir = os.path.join(WORK, "dex")
    unsigned = os.path.join(WORK, "unsigned.apk")
    aligned = os.path.join(WORK, "aligned.apk")
    built = os.path.join(WORK, "built.apk")

    print("[1/6] aapt2 编译资源")
    sh(f"{q(AAPT2)} compile --dir {q(res)} -o {q(res_zip)}", "aapt2 compile")
    sh(f"{q(AAPT2)} link -o {q(base_apk)} -I {q(PLAT)} --manifest {q(manifest)} "
       f"-R {q(res_zip)} --java {q(os.path.join(WORK,'gen'))} --auto-add-overlay", "aapt2 link")

    print("[2/6] javac 编译 Java")
    sh(f"{q(JAVAC)} -encoding UTF-8 -nowarn -source 8 -target 8 -bootclasspath {q(PLAT)} "
       f"-d {q(classes_dir)} {q(src)} {q(rjava)}", "javac")

    print("[3/6] d8 生成 dex")
    sh(f"{q(JAR)} cf {q(classes_jar)} -C {q(classes_dir)} .", "jar")
    sh(f"{q(D8)} --lib {q(PLAT)} --min-api 21 --output {q(dex_dir)} {q(classes_jar)}", "d8")

    print("[4/6] 组装 APK")
    shutil.copy2(base_apk, unsigned)
    n_assets = 0
    with zipfile.ZipFile(unsigned, "a") as z:
        z.write(os.path.join(dex_dir, "classes.dex"), "classes.dex",
                compress_type=zipfile.ZIP_DEFLATED)
        for root, _, files in os.walk(assets):
            for f in files:
                full = os.path.join(root, f)
                rel = "assets/" + os.path.relpath(full, assets).replace("\\", "/")
                ct = zipfile.ZIP_STORED if f.lower().endswith(".webp") else zipfile.ZIP_DEFLATED
                z.write(full, rel, compress_type=ct)
                n_assets += 1
    print(f"     注入 assets {n_assets} 个文件")

    print("[5/6] zipalign")
    sh(f"{q(ZIPALIGN)} -f 4 {q(unsigned)} {q(aligned)}", "zipalign")

    print("[6/6] 签名")
    ks = os.path.join(KEYDIR, "debug.keystore")
    legacy = os.path.join(T, "apkbuild", "debug.keystore")
    if not os.path.exists(ks) and os.path.exists(legacy):
        shutil.copy2(legacy, ks)
        print("     复用原有 debug 签名（保证可覆盖安装旧版本）")
    if not os.path.exists(ks):
        sh(f'{q(KEYTOOL)} -genkeypair -keystore {q(ks)} -storepass android -keypass android '
           f'-alias androiddebugkey -keyalg RSA -keysize 2048 -validity 10000 '
           f'-dname "CN=Android Debug,O=Android,C=US"', "keytool")
    sh(f"{q(APKSIGNER)} sign --ks {q(ks)} --ks-pass pass:android --key-pass pass:android "
       f"--ks-key-alias androiddebugkey --out {q(built)} {q(aligned)}", "apksigner sign")

    out_apk = os.path.join(OUT_DIR, APK_NAME)

    print("\n=========== 校验 ===========")
    out = sh(f"{q(AAPT2)} dump badging {q(built)}", "aapt2 dump badging")
    for line in out.splitlines():
        if any(k in line for k in ("package:", "application-label", "launchable-activity",
                                   "sdkVersion", "targetSdkVersion", "application-icon")):
            print("  " + line.strip())
    v = sh(f"{q(APKSIGNER)} verify --verbose --print-certs {q(built)}", "apksigner verify")
    for line in v.splitlines():
        if any(k in line for k in ("Verified", "Signer #1 certificate DN")):
            print("  " + line.strip())

    shutil.copy2(built, out_apk)
    sz = os.path.getsize(out_apk)
    print(f"\n  产物: {out_apk}\n  体积: {sz/1024:.0f} KB ({sz/1024/1024:.2f} MB)")
    with zipfile.ZipFile(out_apk) as z:
        bad = z.testzip()
        print("  zip 完整性:", "OK" if bad is None else f"损坏 {bad}")
        entries = z.infolist()
        print(f"  条目数: {len(entries)}")
        for i in sorted(entries, key=lambda e: -e.file_size)[:8]:
            mode = "store" if i.compress_type == zipfile.ZIP_STORED else "deflate"
            print(f"    {i.filename:34s} {i.file_size/1024:8.1f} KB  {mode}")


if __name__ == "__main__":
    main()

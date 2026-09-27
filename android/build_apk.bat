@echo off
REM ============================================================
REM  Fengqi Jiuchangjie - Android APK build (Gradle-free)
REM  aapt2 -> javac -> jar -> d8 -> 组装 -> zipalign -> apksigner
REM
REM  依赖：JDK 17 + Android SDK build-tools 34 / platform android-34
REM        默认路径 %TEMP%\jdk17 与 %TEMP%\android-sdk，
REM        如装在别处请改下面的 JDK / SDK 变量。
REM
REM  注意：aapt2 / apksigner 不支持非 ASCII 路径，本工程目录名含中文，
REM        因此先把工程暂存到纯英文临时目录再构建。
REM        推荐直接用仓库里的 Python 脚本（已处理该问题 + 体积优化）：
REM            python _build\build_apk.py
REM ============================================================
setlocal enabledelayedexpansion

set "T=%TEMP%"
set "SDK=%T%\android-sdk"
set "JDK=%T%\jdk17"
set "BT=%SDK%\build-tools\34.0.0"
set "PLAT=%SDK%\platforms\android-34\android.jar"

REM 暂存到纯英文路径
set "PROJ=%T%\fq_manual\proj"
set "WORK=%T%\fq_manual\build"
set "OUT=%T%\fq_manual\out"

echo [0/7] 暂存工程到纯英文路径
if exist "%T%\fq_manual" rmdir /S /Q "%T%\fq_manual"
mkdir "%PROJ%" 2>NUL
xcopy /E /I /Q "%~dp0." "%PROJ%" >NUL
mkdir "%WORK%\gen" 2>NUL
mkdir "%WORK%\classes" 2>NUL
mkdir "%WORK%\dex" 2>NUL
mkdir "%OUT%" 2>NUL

echo [1/7] aapt2 compile + link
"%BT%\aapt2.exe" compile --dir "%PROJ%\res" -o "%WORK%\res.zip"
if errorlevel 1 goto :fail
"%BT%\aapt2.exe" link -o "%WORK%\base.apk" -I "%PLAT%" --manifest "%PROJ%\AndroidManifest.xml" -R "%WORK%\res.zip" --java "%WORK%\gen" --auto-add-overlay
if errorlevel 1 goto :fail

echo [2/7] javac
"%JDK%\bin\javac.exe" -encoding UTF-8 -nowarn -source 8 -target 8 -bootclasspath "%PLAT%" -d "%WORK%\classes" "%PROJ%\src\com\uahz\fengqi\MainActivity.java" "%WORK%\gen\com\uahz\fengqi\R.java"
if errorlevel 1 goto :fail

echo [3/7] jar + d8
"%JDK%\bin\jar.exe" cf "%WORK%\classes.jar" -C "%WORK%\classes" .
set "JAVA_HOME=%JDK%"
set "PATH=%JDK%\bin;%PATH%"
call "%BT%\d8.bat" --lib "%PLAT%" --min-api 21 --output "%WORK%\dex" "%WORK%\classes.jar"
if errorlevel 1 goto :fail

echo [4/7] assemble apk
copy /Y "%WORK%\base.apk" "%WORK%\unsigned.apk" >NUL
"%JDK%\bin\jar.exe" uf "%WORK%\unsigned.apk" -C "%WORK%\dex" classes.dex
REM 注入 assets（index.html + img 背景图）
"%JDK%\bin\jar.exe" uf "%WORK%\unsigned.apk" -C "%PROJ%\assets" index.html img

echo [5/7] zipalign
"%BT%\zipalign.exe" -f 4 "%WORK%\unsigned.apk" "%WORK%\aligned.apk"
if errorlevel 1 goto :fail

echo [6/7] sign
if not exist "%WORK%\debug.keystore" (
  "%JDK%\bin\keytool.exe" -genkeypair -keystore "%WORK%\debug.keystore" -storepass android -keypass android -alias androiddebugkey -keyalg RSA -keysize 2048 -validity 10000 -dname "CN=Android Debug,O=Android,C=US" >NUL 2>&1
)
call "%BT%\apksigner.bat" sign --ks "%WORK%\debug.keystore" --ks-pass pass:android --key-pass pass:android --ks-key-alias androiddebugkey --out "%OUT%\fengqi-jiuchangjie.apk" "%WORK%\aligned.apk"
if errorlevel 1 goto :fail

echo [7/7] verify
"%BT%\aapt2.exe" dump badging "%OUT%\fengqi-jiuchangjie.apk" | findstr /C:"package:" /C:"application-label" /C:"launchable-activity"
call "%BT%\apksigner.bat" verify --verbose "%OUT%\fengqi-jiuchangjie.apk" | findstr /C:"Verified"
echo.
echo === BUILD OK ===
for %%F in ("%OUT%\fengqi-jiuchangjie.apk") do echo APK: %%~nxF  %%~zF bytes
echo 提示：正式发布请把 APK 拷回 03-Android安装包/ 并改名带版本号
goto :eof

:fail
echo.
echo *** BUILD FAILED ***
exit /b 1

@echo off
REM ============================================================
REM  Fengqi Jiuchangjie - Android APK build (Gradle-free)
REM  aapt2 -> javac -> jar -> d8 -> package -> zipalign -> apksigner
REM  Requires: JDK 17 (%TEMP%\jdk17), Android SDK (%TEMP%\android-sdk)
REM ============================================================
setlocal enabledelayedexpansion

set "SDK=%TEMP%\android-sdk"
set "JDK=%TEMP%\jdk17"
set "BT=%SDK%\build-tools\34.0.0"
set "PLAT=%SDK%\platforms\android-34\android.jar"
set "PROJ=F:\Administrator\Documents\代码\android"
set "WORK=%TEMP%\apkbuild"
set "OUT=F:\Administrator\Documents\代码\dist"
set "APKNAME=fengqi-jiuchangjie.apk"

echo [1/7] prepare dirs
if exist "%WORK%" rmdir /S /Q "%WORK%"
mkdir "%WORK%\gen" 2>NUL
mkdir "%WORK%\classes" 2>NUL
mkdir "%WORK%\dex" 2>NUL
mkdir "%OUT%" 2>NUL

echo [2/7] aapt2 compile + link
"%BT%\aapt2.exe" compile --dir "%PROJ%\res" -o "%WORK%\res.zip"
if errorlevel 1 goto :fail
"%BT%\aapt2.exe" link -o "%WORK%\base.apk" -I "%PLAT%" --manifest "%PROJ%\AndroidManifest.xml" -R "%WORK%\res.zip" --java "%WORK%\gen" --auto-add-overlay
if errorlevel 1 goto :fail

echo [3/7] javac
"%JDK%\bin\javac.exe" -encoding UTF-8 -nowarn -source 8 -target 8 -bootclasspath "%PLAT%" -d "%WORK%\classes" "%PROJ%\src\com\uahz\fengqi\MainActivity.java" "%WORK%\gen\com\uahz\fengqi\R.java"
if errorlevel 1 goto :fail

echo [4/7] jar + d8
"%JDK%\bin\jar.exe" cf "%WORK%\classes.jar" -C "%WORK%\classes" .
call "%BT%\d8.bat" --lib "%PLAT%" --min-api 21 --output "%WORK%\dex" "%WORK%\classes.jar"
if errorlevel 1 goto :fail

echo [5/7] assemble apk
copy /Y "%WORK%\base.apk" "%WORK%\unsigned.apk" >NUL
"%JDK%\bin\jar.exe" uf "%WORK%\unsigned.apk" -C "%WORK%\dex" classes.dex
"%JDK%\bin\jar.exe" uf "%WORK%\unsigned.apk" -C "%PROJ%\assets" index.html icon-192.png icon-512.png manifest.json

echo [6/7] zipalign
"%BT%\zipalign.exe" -f 4 "%WORK%\unsigned.apk" "%WORK%\aligned.apk"
if errorlevel 1 goto :fail

echo [7/7] sign
if not exist "%WORK%\debug.keystore" (
  "%JDK%\bin\keytool.exe" -genkeypair -keystore "%WORK%\debug.keystore" -storepass android -keypass android -alias androiddebugkey -keyalg RSA -keysize 2048 -validity 10000 -dname "CN=Android Debug,O=Android,C=US" >NUL 2>&1
)
"%BT%\apksigner.bat" sign --ks "%WORK%\debug.keystore" --ks-pass pass:android --key-pass pass:android --ks-key-alias androiddebugkey --out "%OUT%\%APKNAME%" "%WORK%\aligned.apk"
if errorlevel 1 goto :fail

"%BT%\aapt2.exe" dump badging "%OUT%\%APKNAME%" | findstr /C:"package:" /C:"application-label" /C:"launchable-activity"
echo.
echo === BUILD OK ===
for %%F in ("%OUT%\%APKNAME%") do echo APK: %%~nxF  %%~zF bytes
goto :eof

:fail
echo.
echo *** BUILD FAILED ***
exit /b 1

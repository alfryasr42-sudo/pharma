@echo off
chcp 65001 >nul
echo ================================
echo   بناء RTX - نظام إدارة الصيدلية
echo ================================
echo.

REM Step 1: Build x86 executable with PyInstaller (Windows 7 compatible)
echo [1/3] بناء الملف التنفيذي (32-bit)...
echo Using adang1345/PythonVista Python 3.14.4 for Win7 compatibility

REM Build 32-bit (x86) version
C:\Python314_win7_embed_x86\python.exe -m PyInstaller pharma.spec --clean
if %errorlevel% neq 0 (
    echo ❌ فشل بناء الملف التنفيذي
    pause
    exit /b 1
)

REM Copy x86 DLL and organize output
move /Y dist\PharmaSys.exe dist\PharmaSys_x86.exe >nul 2>&1
if not exist dist_x86 mkdir dist_x86
copy /Y dist\PharmaSys_x86.exe dist_x86\PharmaSys.exe >nul
copy /Y "C:\Python314_win7_embed_x86\api-ms-win-core-path-l1-1-0.dll" dist_x86\api-ms-win-core-path-l1-1-0.dll >nul
echo ✅ تم بناء الملف التنفيذي (32-bit, Windows 7 compatible)

REM Step 2: Create installer with Inno Setup
echo [2/3] بناء مثبت التثبيت...
set ISCC="C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if exist %ISCC% (
    %ISCC% installer.iss
    if %errorlevel% neq 0 (
        echo ❌ فشل بناء المثبت
        pause
        exit /b 1
    )
    echo ✅ تم بناء المثبت: dist\RTX_Setup_v*.exe
) else (
    echo ⚠️ Inno Setup غير مثبت. قم بتثبيته من https://jrsoftware.org
    echo   ثم شغّل: ISCC.exe installer.iss
)

REM Step 3: Done
echo.
echo ================================
echo ✅ اكتمل البناء!
echo ================================
echo.
echo الملفات الناتجة:
echo   - dist\PharmaSys.exe  (تطبيق محمول)
echo   - dist\RTX_Setup_v*.exe  (مثبت التثبيت)
echo.
echo لنشر تحديث:
echo   1. ارفع RTX_Setup_v*.exe إلى GitHub Releases
echo   2. حدث update_manifest.json بالرابط الجديد
echo.
pause

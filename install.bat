@echo off
setlocal

:: Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Python is not installed or not in PATH
    exit /b 1
)

if not exist "build" mkdir build


:: check if FFSVersionManager.exe is running, if running, exit
taskkill /f /im FFSVersionManager.exe >nul 2>&1

:: Package with Nuitka
python -m nuitka ^
    --msvc=latest ^
    --standalone ^
    --onefile ^
    --windows-icon-from-ico=src/res/appicon.ico ^
    --enable-plugin=pyside6 ^
    --include-data-dir=src/res=res ^
    --follow-imports ^
    --output-dir=build ^
    --windows-console-mode=attach ^
    --output-filename=FFSVersionManager.exe ^
    main.py

echo Build complete! Output is in the build directory.

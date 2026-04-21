@echo off
:: VoiceType Windows Build Script
:: Run from project root: build_exe.bat

echo Building VoiceType...

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found in PATH
    pause
    exit /b 1
)

:: Install dependencies
echo Installing dependencies...
pip install -e .

:: Build with PyInstaller
echo Building executable...
pyinstaller ^
    --onefile ^
    --windowed ^
    --name VoiceType ^
    --add-data "voice_type;voice_type" ^
    --hidden-import faster_whisper ^
    --hidden-import sounddevice ^
    --hidden-import soundfile ^
    --hidden-import keyboard ^
    --hidden-import pyperclip ^
    --collect-all faster_whisper ^
    voice_type/__main__.py

echo.
echo Build complete!
echo Output: dist/VoiceType.exe
pause

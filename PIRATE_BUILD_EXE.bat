@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
title PIRATE TOKEN BOT - сборка EXE
echo ==========================================
echo   PIRATE TOKEN BOT - сборка в один EXE
echo ==========================================
echo.

set "PY="
where py >nul 2>nul && set "PY=py"
if not defined PY where python >nul 2>nul && set "PY=python"
if not defined PY goto nopython

echo [1/3] Устанавливаю нужные модули...
%PY% -m pip install --upgrade pip >nul
%PY% -m pip install pyinstaller pyautogui keyboard pillow
if errorlevel 1 goto failed

echo.
echo [2/3] Собираю один EXE-файл, это займёт 1-2 минуты...
%PY% -m PyInstaller --noconfirm --clean --onefile --windowed --name "PIRATE TOKEN BOT" --icon "PIRATE_ICON.ico" --collect-all pyautogui --collect-all keyboard --hidden-import PIL._tkinter_finder --add-data "PIRATE_ICON.ico;." --add-data "PIRATE_ICON.png;." --add-data "PIRATE_ICON_BLACK.ico;." --add-data "PIRATE_ICON_BLACK.png;." --add-data "PIRATE_ICON_WHITE.ico;." --add-data "PIRATE_ICON_WHITE.png;." --add-data "Sound 1.wav;." --add-data "Sound 2.wav;." --add-data "Sound 3.wav;." --add-data "Sound 4.wav;." --add-data "Sound 5.wav;." --add-data "Sound 6.wav;." --add-data "Sound 7.wav;." --add-data "Sound 8.wav;." --add-data "Sound 9.wav;." --add-data "Sound Stop.wav;." PIRATE_TOKEN_BOT.py
if errorlevel 1 goto failed

echo.
echo [3/3] Переношу готовый файл и удаляю временные папки...
if not exist "dist\PIRATE TOKEN BOT.exe" goto failed
move /y "dist\PIRATE TOKEN BOT.exe" "%~dp0PIRATE TOKEN BOT.exe" >nul
rmdir /s /q build 2>nul
rmdir /s /q dist 2>nul
del /q "PIRATE TOKEN BOT.spec" 2>nul

echo.
echo ==========================================
echo   ГОТОВО!  PIRATE TOKEN BOT.exe лежит рядом с этим файлом.
echo   Это один файл: иконка и звуки уже внутри, Python и cmd больше не нужны.
echo   Его можно переносить куда угодно и запускать двойным кликом.
echo   Настройки bot_config.json появятся рядом с EXE.
echo   Если иконка в проводнике старая, переименуйте или переместите EXE: Windows кэширует иконки.
echo ==========================================
pause
exit /b 0

:nopython
echo Python не найден. Он нужен только один раз, чтобы собрать EXE.
where winget >nul 2>nul
if errorlevel 1 goto manualpython
echo Устанавливаю Python автоматически...
winget install -e --id Python.Python.3.12 --silent --accept-package-agreements --accept-source-agreements
echo.
echo Python установлен. Закройте это окно и запустите файл сборки ещё раз.
pause
exit /b 0

:manualpython
echo Установите Python 3.11 или новее с python.org, отметьте Add Python to PATH
echo и запустите этот файл ещё раз.
pause
exit /b 1

:failed
echo.
echo Ошибка сборки. Прокрутите окно вверх и посмотрите сообщения об ошибке.
pause
exit /b 1

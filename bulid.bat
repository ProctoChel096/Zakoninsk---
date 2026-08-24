@echo off
pyinstaller --onefile --windowed ^
    --add-data "templates;templates" ^
    --add-data "data.json;." ^
    --hidden-import=flask ^
    --hidden-import=werkzeug ^
    --hidden-import=keyboard ^
    --hidden-import=psutil ^
    --hidden-import=win32gui ^
    --hidden-import=win32con ^
    --hidden-import=win32process ^
    --hidden-import=win32api ^
    --name "Законинск" ^
    app.py
pause
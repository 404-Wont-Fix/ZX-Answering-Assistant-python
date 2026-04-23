@echo off
REM ZX Answering Assistant - 依赖安装脚本
REM 用于快速安装所有必需的 Python 包

echo ============================================================
echo    ZX Answering Assistant - 依赖安装
echo ============================================================
echo.

REM 检查 Python 是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python，请先安装 Python 3.10+
    pause
    exit /b 1
)

echo [1/4] 检查虚拟环境...
if exist ".venv\Scripts\activate.bat" (
    echo [OK] 虚拟环境已存在
    call .venv\Scripts\activate.bat
) else (
    echo [信息] 未找到虚拟环境，使用系统 Python
)

echo.
echo [2/4] 升级 pip...
python -m pip install --upgrade pip

echo.
echo [3/4] 安装项目依赖...
pip install -r requirements.txt

echo.
echo [4/4] 安装 Playwright 浏览器...
python -m playwright install chromium

echo.
echo ============================================================
echo    安装完成！
echo ============================================================
echo.
echo 现在可以运行程序:
echo    python main.py
echo.
pause

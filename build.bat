@echo off
REM ZX Answering Assistant 构建脚本
REM 自动清理缓存并重新编译

echo ======================================================================
echo    🚀 ZX Answering Assistant 构建脚本
echo ======================================================================
echo.

REM 检查虚拟环境
if not exist ".venv\Scripts\activate.bat" (
    echo ❌ 未找到虚拟环境
    echo 请先运行: python -m venv .venv
    pause
    exit /b 1
)

echo ✓ 虚拟环境已找到
echo.

REM 激活虚拟环境
call .venv\Scripts\activate.bat

echo 📋 正在清理旧的构建文件...
if exist "build\windows" (
    echo   - 删除 build/windows
    rmdir /s /q "build\windows"
)
if exist "build\flutter" (
    echo   - 删除 build/flutter (模板缓存)
    rmdir /s /q "build\flutter"
)
if exist "dist" (
    echo   - 删除 dist
    rmdir /s /q "dist"
)

echo ✓ 清理完成
echo.

echo 📦 正在编译应用（详细模式）...
echo.
flet build windows --project=ZX-Answering-Assistant --verbose

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ======================================================================
    echo    ✅ 编译成功！
    echo ======================================================================
    echo.
    echo 📂 编译产物位置: build\windows\**\Release
    echo.
    echo 💡 提示: 可执行文件在 build\windows\x64\runner\Release 目录中
    echo.
) else (
    echo.
    echo ======================================================================
    echo    ❌ 编译失败
    echo ======================================================================
    echo.
    echo 💡 请检查错误信息并重试
    echo.
)

pause

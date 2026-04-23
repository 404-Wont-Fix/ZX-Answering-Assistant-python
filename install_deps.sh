#!/bin/bash
# ZX Answering Assistant - 依赖安装脚本
# 用于快速安装所有必需的 Python 包

echo "============================================================"
echo "   ZX Answering Assistant - 依赖安装"
echo "============================================================"
echo ""

# 检查 Python 是否安装
if ! command -v python3 &> /dev/null; then
    echo "[错误] 未找到 Python3，请先安装 Python 3.10+"
    exit 1
fi

echo "[1/4] 检查虚拟环境..."
if [ -f ".venv/bin/activate" ]; then
    echo "[OK] 虚拟环境已存在"
    source .venv/bin/activate
else
    echo "[信息] 未找到虚拟环境，使用系统 Python"
fi

echo ""
echo "[2/4] 升级 pip..."
python3 -m pip install --upgrade pip

echo ""
echo "[3/4] 安装项目依赖..."
pip3 install -r requirements.txt

echo ""
echo "[4/4] 安装 Playwright 浏览器..."
python3 -m playwright install chromium

echo ""
echo "============================================================"
echo "   安装完成！"
echo "============================================================"
echo ""
echo "现在可以运行程序:"
echo "    python3 main.py"
echo ""

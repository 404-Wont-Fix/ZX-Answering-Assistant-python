"""
ZX Answering Assistant - 主程序入口
智能答题助手系统
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 导入登录模块和题目提取模块
from src.login import get_access_token
from src.extract import extract_questions


def main():
    while True:
        print("欢迎使用智能答题助手系统")
        print("0. 获取access_token")
        print("1. 开始答题")
        print("2. 题目提取")
        print("4. 设置")
        print("5. 退出系统")
        choice = input("请选择操作：")
        if choice == "0":
            # 获取access_token
            print("正在获取access_token...")
            access_token = get_access_token()
            if access_token:
                print(f"\n✅ 获取access_token成功！")
                print(f"access_token: {access_token}")
                print(f"token类型: Bearer")
                print(f"有效期: 5小时 (18000秒)")
            else:
                print(f"\n❌ 获取access_token失败！")
        elif choice == "1":
            # 调用开始答题功能
            print("开始答题功能尚未实现")
        elif choice == "2":
            # 题目提取功能
            extract_questions()
        elif choice == "4":
            # 设置功能
            print("设置功能尚未实现")
        elif choice == "5":
            # 退出系统
            print("退出系统，再见！")
            break
        else:
            print("无效的选择，请重新输入")


if __name__ == "__main__":
    main()

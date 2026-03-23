"""
WeBan 独立运行器

在独立终端窗口中运行 WeBan 模块，保持其 CLI 交互能力
"""

import sys
import os
import json
import subprocess
from pathlib import Path
from typing import Dict, List, Any


class WeBanRunner:
    """WeBan 独立运行器"""

    def __init__(self):
        """初始化运行器"""
        self.weban_path = Path(__file__).parent / "WeBan"
        self.runner_script = self.weban_path / "run_weban.py"

    def create_runner_script(self):
        """创建 WeBan 运行脚本（如果不存在）"""
        if self.runner_script.exists():
            return

        script_content = '''#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
WeBan 独立运行脚本

在独立终端中运行 WeBan，保持完整的 CLI 交互能力
"""

import sys
import os
import json
import time
from pathlib import Path

# 添加 WeBan 模块路径
weban_path = Path(__file__).parent
if str(weban_path) not in sys.path:
    sys.path.insert(0, str(weban_path))

from client import WeBanClient

def load_config_from_file(config_file: str) -> list:
    """从配置文件加载配置"""
    with open(config_file, 'r', encoding='utf-8') as f:
        return json.load(f)

def run_account(config: dict, index: int):
    """运行单个账号"""
    print(f"\\n{'='*60}")
    print(f"开始处理账号 {index + 1}")
    print(f"{'='*60}\\n")

    tenant_name = config.get("tenant_name", "").strip()
    account = config.get("account", "").strip()
    password = config.get("password", "").strip()
    user = config.get("user", {})
    study = config.get("study", True)
    study_time = int(config.get("study_time", 20))
    restudy_time = int(config.get("restudy_time", 0))
    exam = config.get("exam", True)
    exam_use_time = int(config.get("exam_use_time", 250))

    if user.get("tenantName"):
        tenant_name = user["tenantName"]

    try:
        # 创建客户端（使用 print 作为 logger）
        if all([tenant_name, user.get("userId"), user.get("token")]):
            print(f"[账号 {index + 1}] 使用 Token 登录")
            client = WeBanClient(tenant_name, user=user)
        elif all([tenant_name, account, password]):
            print(f"[账号 {index + 1}] 使用密码登录")
            client = WeBanClient(tenant_name, account, password)
        else:
            print(f"[账号 {index + 1}] ❌ 缺少必要的配置信息")
            return False

        # 登录
        if not client.login():
            print(f"[账号 {index + 1}] ❌ 登录失败")
            return False

        print(f"[账号 {index + 1}] ✅ 登录成功，开始同步答案")
        client.sync_answers()

        # 学习
        if study:
            print(f"[账号 {index + 1}] 开始学习 (每个任务时长: {study_time}秒)")
            client.run_study(study_time, restudy_time)

        # 考试
        if exam:
            print(f"[账号 {index + 1}] 开始考试 (总时长: {exam_use_time}秒)")
            client.run_exam(exam_use_time)

        print(f"[账号 {index + 1}] 最终同步答案")
        client.sync_answers()

        print(f"[账号 {index + 1}] ✅ 执行完成\\n")
        return True

    except Exception as e:
        print(f"[账号 {index + 1}] ❌ 运行失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("用法: python run_weban.py <config_file>")
        print("配置文件格式为 JSON，包含账号配置列表")
        sys.exit(1)

    config_file = sys.argv[1]
    if not os.path.exists(config_file):
        print(f"❌ 配置文件不存在: {config_file}")
        sys.exit(1)

    # 加载配置
    configs = load_config_from_file(config_file)
    print(f"\\n🚀 WeBan 独立运行器")
    print(f"📋 共 {len(configs)} 个账号配置")
    print(f"⏰ 开始时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\\n")

    # 逐个处理账号
    success_count = 0
    failed_count = 0

    for i, config in enumerate(configs):
        try:
            result = run_account(config, i)
            if result:
                success_count += 1
            else:
                failed_count += 1
        except KeyboardInterrupt:
            print(f"\\n⚠️ 用户中断执行")
            break
        except Exception as e:
            print(f"\\n❌ 账号 {i+1} 执行异常: {e}")
            failed_count += 1

    # 总结
    print(f"\\n{'='*60}")
    print(f"✅ 所有账号执行完成！")
    print(f"📊 成功: {success_count}，失败: {failed_count}")
    print(f"⏰ 结束时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\\n")

    # 等待用户确认
    input("按 Enter 键关闭窗口...")

if __name__ == "__main__":
    main()
'''
        with open(self.runner_script, 'w', encoding='utf-8') as f:
            f.write(script_content)

        print(f"✅ 创建 WeBan 运行脚本: {self.runner_script}")

    def run_in_terminal(self, configs: List[Dict[str, Any]]) -> subprocess.Popen:
        """
        在独立终端窗口中运行 WeBan

        Args:
            configs: 账号配置列表

        Returns:
            subprocess.Popen 对象（或伪进程对象）
        """
        # 确保运行脚本存在
        self.create_runner_script()

        # 将配置保存到临时文件
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
            json.dump(configs, f, ensure_ascii=False, indent=2)
            config_file = f.name

        try:
            # 根据操作系统选择启动方式
            if sys.platform == "win32":
                # Windows: 使用 start 命令在新窗口中运行
                # 设置窗口标题，方便后续查找和关闭
                cmd = f'start "WeBan 独立终端 - {configs[0].get("tenant_name", "Unknown")}" /D "{os.getcwd()}" "{sys.executable}" "{self.runner_script}" "{config_file}"'
                print(f"[WeBan] 启动命令: {cmd}")

                # 使用 shell=True 执行 start 命令
                # 注意：start 命令会立即返回，无法获取真实的进程句柄
                # 所以我们创建一个伪进程对象来管理
                subprocess.Popen(
                    cmd,
                    shell=True,
                    creationflags=subprocess.CREATE_NEW_CONSOLE
                )

                # 创建伪进程对象，用于后续管理
                class PseudoProcess:
                    def __init__(self, config_file, runner):
                        self.config_file = config_file
                        self.runner = runner
                        self.alive = True

                    def kill(self):
                        """尝试关闭 WeBan 终端窗口"""
                        self.alive = False
                        self.runner._kill_weban_terminal()

                    def poll(self):
                        """检查进程状态（伪实现）"""
                        return None if self.alive else 0

                process = PseudoProcess(config_file, self)

            else:
                # Linux/Mac: 使用 gnome-terminal 或 xterm
                terminal_commands = [
                    ['gnome-terminal', '--'],
                    ['xterm', '-e'],
                    ['konsole', '-e'],
                ]

                process = None
                for term_cmd in terminal_commands:
                    try:
                        cmd = term_cmd + [sys.executable, str(self.runner_script), config_file]
                        process = subprocess.Popen(cmd)
                        break
                    except FileNotFoundError:
                        continue

                if process is None:
                    raise RuntimeError("无法找到终端模拟器（gnome-terminal、xterm、konsole）")

            return process

        except Exception as e:
            # 清理临时文件
            try:
                os.unlink(config_file)
            except:
                pass
            raise e

    def _kill_weban_terminal(self):
        """强制关闭 WeBan 终端窗口（Windows）"""
        if sys.platform != "win32":
            return

        try:
            # 使用 taskkill 关闭标题包含 "WeBan" 的窗口
            result = subprocess.run(
                ['taskkill', '/F', '/FI', 'WINDOWTITLE eq WeBan*'],
                capture_output=True,
                text=True,
                shell=True
            )
            print(f"[WeBan] 终端关闭结果: {result.stdout}")
        except Exception as e:
            print(f"[WeBan] 关闭终端失败: {e}")

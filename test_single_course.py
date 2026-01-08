"""
测试单个课程提取功能
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.extract import extract_single_course


if __name__ == "__main__":
    print("开始测试单个课程提取功能...")
    print("="*60)
    
    result = extract_single_course()
    
    print("="*60)
    if result:
        print(f"\n✅ 测试成功！班级ID: {result}")
    else:
        print("\n❌ 测试失败！")

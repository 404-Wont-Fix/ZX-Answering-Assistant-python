"""
测试导出功能
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.export import DataExporter


def test_export():
    """测试导出功能"""
    print("测试导出功能")
    print("="*60)
    
    # 创建测试数据
    class_info = {
        "id": "test_class_001",
        "className": "测试班级_2024级",
        "grade": "2024",
        "schoolName": "云南林业职业技术学院",
        "stats": 10
    }
    
    course_info = {
        "courseID": "course_001",
        "courseName": "测试课程",
        "knowledgeSum": 5,
        "shulian": 3
    }
    
    chapters = [
        {
            "chapterID": "chapter_001",
            "courseID": "course_001",
            "chapterTitle": "第一章",
            "chapterContent": "测试章节内容",
            "knowledgeCount": 2,
            "completCount": 1,
            "passCount": 1
        },
        {
            "chapterID": "chapter_002",
            "courseID": "course_001",
            "chapterTitle": "第二章",
            "chapterContent": "测试章节内容2",
            "knowledgeCount": 3,
            "completCount": 2,
            "passCount": 1
        }
    ]
    
    knowledges = [
        {
            "KnowledgeID": "knowledge_001",
            "ChapterID": "chapter_001",
            "Knowledge": "测试知识点1",
            "OrderNumber": 1,
            "completCount": 1,
            "passCount": 1
        },
        {
            "KnowledgeID": "knowledge_002",
            "ChapterID": "chapter_001",
            "Knowledge": "测试知识点2",
            "OrderNumber": 2,
            "completCount": 0,
            "passCount": 0
        },
        {
            "KnowledgeID": "knowledge_003",
            "ChapterID": "chapter_002",
            "Knowledge": "测试知识点3",
            "OrderNumber": 1,
            "completCount": 1,
            "passCount": 0
        }
    ]
    
    questions = {
        "knowledge_001": [
            {
                "QuestionID": "question_001",
                "QuestionTitle": "测试题目1",
                "sumCount": 10,
                "PassCount": 5
            }
        ],
        "knowledge_002": [],
        "knowledge_003": [
            {
                "QuestionID": "question_002",
                "QuestionTitle": "测试题目2",
                "sumCount": 8,
                "PassCount": 3
            }
        ]
    }
    
    options = {
        "question_001": [
            {
                "id": "option_001",
                "questionsID": "question_001",
                "oppentionContent": "选项A",
                "isTrue": True,
                "oppentionOrder": 1,
                "tenantID": 32
            },
            {
                "id": "option_002",
                "questionsID": "question_001",
                "oppentionContent": "选项B",
                "isTrue": False,
                "oppentionOrder": 2,
                "tenantID": 32
            }
        ],
        "question_002": [
            {
                "id": "option_003",
                "questionsID": "question_002",
                "oppentionContent": "选项C",
                "isTrue": False,
                "oppentionOrder": 1,
                "tenantID": 32
            },
            {
                "id": "option_004",
                "questionsID": "question_002",
                "oppentionContent": "选项D",
                "isTrue": True,
                "oppentionOrder": 2,
                "tenantID": 32
            }
        ]
    }
    
    # 创建导出器
    exporter = DataExporter()
    
    # 测试导出单个课程（使用新的export_data方法）
    print("\n测试导出单个课程数据（使用export_data方法）...")
    single_course_data = {
        "class_info": class_info,
        "course_info": course_info,
        "chapters": chapters,
        "knowledges": knowledges,
        "questions": questions,
        "options": options
    }
    file_path = exporter.export_data(single_course_data)
    
    print(f"\n✅ 测试完成！")
    print(f"导出的文件路径：{file_path}")
    
    # 读取并显示导出的文件内容
    print("\n" + "="*60)
    print("导出的文件内容：")
    print("="*60)
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
        print(content)


if __name__ == "__main__":
    test_export()

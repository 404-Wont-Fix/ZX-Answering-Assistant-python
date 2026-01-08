"""
题库导入模块
用于导入和解析导出的题库JSON文件
"""

from typing import Dict, List, Optional
from src.file_handler import FileHandler


class QuestionBankImporter:
    """题库导入器"""
    
    def __init__(self):
        self.data = None
        self.bank_type = None  # "single" 或 "multiple"
        self.file_handler = FileHandler()
    
    def import_from_file(self, file_path: str) -> bool:
        """
        从JSON文件导入题库
        
        Args:
            file_path: JSON文件路径
            
        Returns:
            bool: 导入是否成功
        """
        # 使用文件处理器读取JSON文件
        self.data = self.file_handler.read_json(file_path)
        
        if self.data is None:
            return False
        
        # 识别题库类型
        self._detect_bank_type()
        
        return True
    
    def _detect_bank_type(self):
        """
        识别题库类型
        
        根据数据结构判断是单个课程还是多个课程
        """
        if not self.data:
            self.bank_type = None
            return
        
        # 打印调试信息
        print(f"🔍 调试信息：数据结构的顶层键：{list(self.data.keys())}")
        
        # 检查是否包含course_list字段（多课程）
        if "course_list" in self.data:
            self.bank_type = "multiple"
        elif "class" in self.data:
            print(f"🔍 调试信息：class字段的内容：{list(self.data['class'].keys())}")
            if "course" in self.data["class"]:
                self.bank_type = "single"
            else:
                print(f"❌ class字段中不存在course字段")
                self.bank_type = "unknown"
        else:
            print(f"❌ 数据中不存在class或course_list字段")
            self.bank_type = "unknown"
    
    def get_bank_type(self) -> Optional[str]:
        """
        获取题库类型
        
        Returns:
            str: "single"（单个课程）或 "multiple"（多个课程）
        """
        return self.bank_type
    
    def parse_single_course(self) -> Optional[Dict]:
        """
        解析单个课程的题库
        
        Returns:
            Dict: 解析后的题库数据
        """
        if self.bank_type != "single":
            return None
        
        class_info = self.data.get("class", {})
        course_info = class_info.get("course", {})
        chapters = course_info.get("chapters", [])
        
        return {
            "class": {
                "id": class_info.get("id", ""),
                "name": class_info.get("name", ""),
                "grade": class_info.get("grade", ""),
                "schoolName": class_info.get("schoolName", "")
            },
            "course": {
                "courseID": course_info.get("courseID", ""),
                "courseName": course_info.get("courseName", ""),
                "knowledgeSum": course_info.get("knowledgeSum", 0),
                "shulian": course_info.get("shulian", 0)
            },
            "chapters": chapters,
            "statistics": self._calculate_single_course_statistics(chapters)
        }
    
    def parse_multiple_courses(self) -> Optional[Dict]:
        """
        解析多个课程的题库
        
        Returns:
            Dict: 解析后的题库数据
        """
        if self.bank_type != "multiple":
            return None
        
        class_info = self.data.get("class", {})
        course_list = self.data.get("course_list", [])
        chapters = self.data.get("chapters", [])
        
        return {
            "class": {
                "id": class_info.get("id", ""),
                "name": class_info.get("name", ""),
                "grade": class_info.get("grade", ""),
                "schoolName": class_info.get("schoolName", "")
            },
            "courses": course_list,
            "chapters": chapters,
            "statistics": self._calculate_multiple_courses_statistics(course_list, chapters)
        }
    
    def _calculate_single_course_statistics(self, chapters: List[Dict]) -> Dict:
        """
        计算单个课程的统计数据
        
        Args:
            chapters: 章节列表
            
        Returns:
            Dict: 统计数据
        """
        total_chapters = len(chapters)
        total_knowledges = 0
        total_questions = 0
        total_options = 0
        
        for chapter in chapters:
            knowledges = chapter.get("knowledges", [])
            total_knowledges += len(knowledges)
            
            for knowledge in knowledges:
                questions = knowledge.get("questions", [])
                total_questions += len(questions)
                
                for question in questions:
                    options = question.get("options", [])
                    total_options += len(options)
        
        return {
            "totalChapters": total_chapters,
            "totalKnowledges": total_knowledges,
            "totalQuestions": total_questions,
            "totalOptions": total_options
        }
    
    def _calculate_multiple_courses_statistics(self, course_list: List[Dict], chapters: List[Dict]) -> Dict:
        """
        计算多个课程的统计数据
        
        Args:
            course_list: 课程列表
            chapters: 章节列表
            
        Returns:
            Dict: 统计数据
        """
        total_courses = len(course_list)
        total_chapters = len(chapters)
        total_knowledges = 0
        total_questions = 0
        total_options = 0
        
        for chapter in chapters:
            knowledges = chapter.get("knowledges", [])
            total_knowledges += len(knowledges)
            
            for knowledge in knowledges:
                questions = knowledge.get("questions", [])
                total_questions += len(questions)
                
                for question in questions:
                    options = question.get("options", [])
                    total_options += len(options)
        
        return {
            "totalCourses": total_courses,
            "totalChapters": total_chapters,
            "totalKnowledges": total_knowledges,
            "totalQuestions": total_questions,
            "totalOptions": total_options
        }
    
    def format_output(self) -> str:
        """
        格式化输出题库信息
        
        Returns:
            str: 格式化后的题库信息
        """
        if not self.data or not self.bank_type:
            return "❌ 没有可显示的题库数据"
        
        output = []
        output.append("=" * 80)
        output.append("📚 题库信息")
        output.append("=" * 80)
        
        if self.bank_type == "single":
            output.append(self._format_single_course())
        elif self.bank_type == "multiple":
            output.append(self._format_multiple_courses())
        else:
            output.append("❌ 未知的题库类型")
        
        output.append("=" * 80)
        return "\n".join(output)
    
    def _format_single_course(self) -> str:
        """
        格式化输出单个课程的题库
        
        Returns:
            str: 格式化后的题库信息
        """
        parsed_data = self.parse_single_course()
        if not parsed_data:
            return "❌ 解析单个课程题库失败"
        
        output = []
        
        # 班级信息
        class_info = parsed_data["class"]
        output.append("\n📖 班级信息：")
        output.append(f"  班级ID：{class_info['id']}")
        output.append(f"  班级名称：{class_info['name']}")
        output.append(f"  年级：{class_info['grade']}")
        output.append(f"  学校：{class_info['schoolName']}")
        
        # 课程信息
        course_info = parsed_data["course"]
        output.append("\n📚 课程信息：")
        output.append(f"  课程ID：{course_info['courseID']}")
        output.append(f"  课程名称：{course_info['courseName']}")
        output.append(f"  知识点总数：{course_info['knowledgeSum']}")
        output.append(f"  已完成：{course_info['shulian']}")
        
        # 统计信息
        stats = parsed_data["statistics"]
        output.append("\n📊 统计信息：")
        output.append(f"  章节数：{stats['totalChapters']}")
        output.append(f"  知识点数：{stats['totalKnowledges']}")
        output.append(f"  题目数：{stats['totalQuestions']}")
        output.append(f"  选项数：{stats['totalOptions']}")
        
        # 章节详情
        output.append("\n📑 章节详情：")
        for i, chapter in enumerate(parsed_data["chapters"], 1):
            output.append(f"\n  第{i}章：{chapter['chapterTitle']}")
            output.append(f"    章节ID：{chapter['chapterID']}")
            output.append(f"    知识点数：{len(chapter.get('knowledges', []))}")
            
            # 知识点详情
            knowledges = chapter.get("knowledges", [])
            for j, knowledge in enumerate(knowledges, 1):
                output.append(f"    知识点{j}：{knowledge['Knowledge']}")
                output.append(f"      知识点ID：{knowledge['KnowledgeID']}")
                output.append(f"      题目数：{len(knowledge.get('questions', []))}")
                
                # 题目详情
                questions = knowledge.get("questions", [])
                for k, question in enumerate(questions, 1):
                    output.append(f"      题目{k}：{question['QuestionTitle']}")
                    output.append(f"        题目ID：{question['QuestionID']}")
                    output.append(f"        选项数：{len(question.get('options', []))}")
                    
                    # 选项详情
                    options = question.get("options", [])
                    for option in options:
                        is_correct = "✅" if option.get("isTrue", False) else "❌"
                        output.append(f"        {is_correct} 选项{option.get('oppentionOrder', 0)}：{option.get('oppentionContent', '')}")
        
        return "\n".join(output)
    
    def _format_multiple_courses(self) -> str:
        """
        格式化输出多个课程的题库
        
        Returns:
            str: 格式化后的题库信息
        """
        parsed_data = self.parse_multiple_courses()
        if not parsed_data:
            return "❌ 解析多个课程题库失败"
        
        output = []
        
        # 班级信息
        class_info = parsed_data["class"]
        output.append("\n📖 班级信息：")
        output.append(f"  班级ID：{class_info['id']}")
        output.append(f"  班级名称：{class_info['name']}")
        output.append(f"  年级：{class_info['grade']}")
        output.append(f"  学校：{class_info['schoolName']}")
        
        # 统计信息
        stats = parsed_data["statistics"]
        output.append("\n📊 统计信息：")
        output.append(f"  课程数：{stats['totalCourses']}")
        output.append(f"  章节数：{stats['totalChapters']}")
        output.append(f"  知识点数：{stats['totalKnowledges']}")
        output.append(f"  题目数：{stats['totalQuestions']}")
        output.append(f"  选项数：{stats['totalOptions']}")
        
        # 课程列表
        output.append("\n📚 课程列表：")
        for i, course in enumerate(parsed_data["courses"], 1):
            output.append(f"\n  课程{i}：{course['courseName']}")
            output.append(f"    课程ID：{course['courseID']}")
            output.append(f"    知识点总数：{course.get('knowledgeSum', 0)}")
            output.append(f"    已完成：{course.get('shulian', 0)}")
        
        # 章节详情
        output.append("\n📑 章节详情：")
        for i, chapter in enumerate(parsed_data["chapters"], 1):
            output.append(f"\n  第{i}章：{chapter['chapterTitle']}")
            output.append(f"    章节ID：{chapter['chapterID']}")
            output.append(f"    知识点数：{len(chapter.get('knowledges', []))}")
            
            # 知识点详情
            knowledges = chapter.get("knowledges", [])
            for j, knowledge in enumerate(knowledges, 1):
                output.append(f"    知识点{j}：{knowledge['Knowledge']}")
                output.append(f"      知识点ID：{knowledge['KnowledgeID']}")
                output.append(f"      题目数：{len(knowledge.get('questions', []))}")
                
                # 题目详情
                questions = knowledge.get("questions", [])
                for k, question in enumerate(questions, 1):
                    output.append(f"      题目{k}：{question['QuestionTitle']}")
                    output.append(f"        题目ID：{question['QuestionID']}")
                    output.append(f"        选项数：{len(question.get('options', []))}")
                    
                    # 选项详情
                    options = question.get("options", [])
                    for option in options:
                        is_correct = "✅" if option.get("isTrue", False) else "❌"
                        output.append(f"        {is_correct} 选项{option.get('oppentionOrder', 0)}：{option.get('oppentionContent', '')}")
        
        return "\n".join(output)

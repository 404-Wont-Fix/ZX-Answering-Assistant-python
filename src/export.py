"""
导出模块
用于将提取的题目数据导出为JSON文件
"""

from typing import Dict, List, Optional
from datetime import datetime
from src.file_handler import FileHandler


class DataExporter:
    """数据导出器"""
    
    def __init__(self, output_dir: str = "output"):
        """
        初始化导出器
        
        Args:
            output_dir: 输出目录，默认为"output"
        """
        self.output_dir = output_dir
        self.file_handler = FileHandler()
        # 确保输出目录存在
        self.file_handler.create_directory(output_dir)
        
    def export_to_json(self, data: Dict, filename: Optional[str] = None) -> str:
        """
        将数据导出为JSON文件
        
        Args:
            data: 要导出的数据字典
            filename: 文件名，如果不提供则自动生成
            
        Returns:
            str: 导出的文件路径
        """
        if filename is None:
            # 自动生成文件名，包含时间戳
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"questions_{timestamp}.json"
        
        # 确保文件名以.json结尾
        if not filename.endswith(".json"):
            filename += ".json"
        
        # 构建完整的文件路径
        file_path = f"{self.output_dir}/{filename}"
        
        # 使用文件处理器写入JSON文件
        success = self.file_handler.write_json(data, file_path, indent=2)
        
        if success:
            print(f"✅ 数据已成功导出到：{file_path}")
            return file_path
        else:
            raise Exception("导出文件失败")
    
    def export_data(self, extracted_data: Dict, filename: Optional[str] = None) -> str:
        """
        自动判断数据类型并导出
        
        Args:
            extracted_data: 提取的数据字典
            filename: 文件名，如果不提供则自动生成
            
        Returns:
            str: 导出的文件路径
        """
        # 判断数据类型
        if "course_info" in extracted_data:
            # 单个课程数据
            return self.export_single_course(
                class_info=extracted_data["class_info"],
                course_info=extracted_data["course_info"],
                chapters=extracted_data["chapters"],
                knowledges=extracted_data["knowledges"],
                questions=extracted_data["questions"],
                options=extracted_data["options"],
                filename=filename
            )
        elif "course_list" in extracted_data:
            # 全部课程数据
            return self.export_all_courses(
                class_info=extracted_data["class_info"],
                course_list=extracted_data["course_list"],
                chapters=extracted_data["chapters"],
                knowledges=extracted_data["knowledges"],
                questions=extracted_data["questions"],
                options=extracted_data["options"],
                filename=filename
            )
        else:
            raise ValueError("无法识别的数据格式")
    
    def export_single_course(self, class_info: Dict, course_info: Dict, 
                            chapters: List[Dict], knowledges: List[Dict],
                            questions: Dict, options: Dict,
                            filename: Optional[str] = None) -> str:
        """
        导出单个课程的数据
        
        Args:
            class_info: 班级信息
            course_info: 课程信息
            chapters: 章节列表
            knowledges: 知识点列表
            questions: 题目字典，key为knowledge_id，value为题目列表
            options: 选项字典，key为question_id，value为选项列表
            filename: 文件名
            
        Returns:
            str: 导出的文件路径
        """
        # 构建数据结构
        data = {
            "class": {
                "id": class_info.get("id", ""),
                "name": class_info.get("className", ""),
                "grade": class_info.get("grade", ""),
                "schoolName": class_info.get("schoolName", ""),
                "course": {
                    "courseID": course_info.get("courseID", ""),
                    "courseName": course_info.get("courseName", ""),
                    "knowledgeSum": course_info.get("knowledgeSum", 0),
                    "shulian": course_info.get("shulian", 0),
                    "chapters": []
                }
            }
        }
        
        # 按章节组织数据
        chapter_dict = {chapter.get("chapterID", ""): chapter for chapter in chapters}
        
        # 按章节分组知识点
        chapter_knowledges = {}
        for knowledge in knowledges:
            chapter_id = knowledge.get("ChapterID", "")
            if chapter_id not in chapter_knowledges:
                chapter_knowledges[chapter_id] = []
            chapter_knowledges[chapter_id].append(knowledge)
        
        # 构建章节数据
        for chapter_id, chapter in chapter_dict.items():
            chapter_knowledges_list = chapter_knowledges.get(chapter_id, [])
            
            chapter_data = {
                "chapterID": chapter.get("chapterID", ""),
                "chapterTitle": chapter.get("chapterTitle", ""),
                "chapterContent": chapter.get("chapterContent", ""),
                "knowledgeCount": chapter.get("knowledgeCount", 0),
                "completCount": chapter.get("completCount", 0),
                "passCount": chapter.get("passCount", 0),
                "knowledges": []
            }
            
            # 添加该章节的知识点
            if chapter_id in chapter_knowledges:
                for knowledge in chapter_knowledges[chapter_id]:
                    knowledge_id = knowledge.get("KnowledgeID", "")
                    
                    knowledge_data = {
                        "KnowledgeID": knowledge_id,
                        "Knowledge": knowledge.get("Knowledge", ""),
                        "OrderNumber": knowledge.get("OrderNumber", 0),
                        "completCount": knowledge.get("completCount", 0),
                        "passCount": knowledge.get("passCount", 0),
                        "questions": []
                    }
                    
                    # 添加该知识点的题目
                    if knowledge_id in questions:
                        for question in questions[knowledge_id]:
                            question_id = question.get("QuestionID", "")
                            
                            question_data = {
                                "QuestionID": question_id,
                                "QuestionTitle": question.get("QuestionTitle", ""),
                                "sumCount": question.get("sumCount", 0),
                                "PassCount": question.get("PassCount", 0),
                                "options": []
                            }
                            
                            # 添加该题目的选项
                            if question_id in options:
                                for option in options[question_id]:
                                    option_data = {
                                        "id": option.get("id", ""),
                                        "questionsID": option.get("questionsID", ""),
                                        "oppentionContent": option.get("oppentionContent", ""),
                                        "isTrue": option.get("isTrue", False),
                                        "oppentionOrder": option.get("oppentionOrder", 0)
                                    }
                                    question_data["options"].append(option_data)
                            
                            knowledge_data["questions"].append(question_data)
                    
                    chapter_data["knowledges"].append(knowledge_data)
            
            data["class"]["course"]["chapters"].append(chapter_data)
        
        # 生成文件名
        if filename is None:
            class_name = class_info.get("className", "").replace(" ", "_")
            course_name = course_info.get("courseName", "").replace(" ", "_")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{class_name}_{course_name}_{timestamp}.json"
        
        return self.export_to_json(data, filename)
    
    def export_all_courses(self, class_info: Dict, course_list: List[Dict],
                          chapters: List[Dict], knowledges: List[Dict],
                          questions: Dict, options: Dict,
                          filename: Optional[str] = None) -> str:
        """
        导出所有课程的数据
        
        Args:
            class_info: 班级信息
            course_list: 课程列表
            chapters: 章节列表
            knowledges: 知识点列表
            questions: 题目字典，key为knowledge_id，value为题目列表
            options: 选项字典，key为question_id，value为选项列表
            filename: 文件名
            
        Returns:
            str: 导出的文件路径
        """
        # 构建数据结构
        data = {
            "class": {
                "id": class_info.get("id", ""),
                "name": class_info.get("className", ""),
                "grade": class_info.get("grade", ""),
                "schoolName": class_info.get("schoolName", "")
            },
            "courses": [],
            "exportTime": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # 按课程分组章节
        course_chapters = {}
        for chapter in chapters:
            course_id = chapter.get("courseID", "")
            if course_id not in course_chapters:
                course_chapters[course_id] = []
            course_chapters[course_id].append(chapter)
        
        # 按章节分组知识点
        chapter_knowledges = {}
        for knowledge in knowledges:
            chapter_id = knowledge.get("ChapterID", "")
            if chapter_id not in chapter_knowledges:
                chapter_knowledges[chapter_id] = []
            chapter_knowledges[chapter_id].append(knowledge)
        
        # 为每个课程构建数据
        for course in course_list:
            course_id = course.get("courseID", "")
            course_data = {
                "courseID": course_id,
                "courseName": course.get("courseName", ""),
                "knowledgeSum": course.get("knowledgeSum", 0),
                "shulian": course.get("shulian", 0),
                "chapters": []
            }
            
            # 添加该课程的章节
            if course_id in course_chapters:
                for chapter in course_chapters[course_id]:
                    chapter_id = chapter.get("chapterID", "")
                    chapter_data = {
                        "chapterID": chapter_id,
                        "chapterTitle": chapter.get("chapterTitle", ""),
                        "chapterContent": chapter.get("chapterContent", ""),
                        "knowledgeCount": chapter.get("knowledgeCount", 0),
                        "completCount": chapter.get("completCount", 0),
                        "passCount": chapter.get("passCount", 0),
                        "knowledges": []
                    }
                    
                    # 添加该章节的知识点
                    if chapter_id in chapter_knowledges:
                        for knowledge in chapter_knowledges[chapter_id]:
                            knowledge_id = knowledge.get("KnowledgeID", "")
                            knowledge_data = {
                                "KnowledgeID": knowledge_id,
                                "Knowledge": knowledge.get("Knowledge", ""),
                                "OrderNumber": knowledge.get("OrderNumber", 0),
                                "completCount": knowledge.get("completCount", 0),
                                "passCount": knowledge.get("passCount", 0),
                                "questions": []
                            }
                            
                            # 添加该知识点的题目
                            if knowledge_id in questions:
                                for question in questions[knowledge_id]:
                                    question_id = question.get("QuestionID", "")
                                    question_data = {
                                        "QuestionID": question_id,
                                        "QuestionTitle": question.get("QuestionTitle", ""),
                                        "sumCount": question.get("sumCount", 0),
                                        "PassCount": question.get("PassCount", 0),
                                        "options": []
                                    }
                                    
                                    # 添加该题目的选项
                                    if question_id in options:
                                        for option in options[question_id]:
                                            option_data = {
                                                "id": option.get("id", ""),
                                                "questionsID": option.get("questionsID", ""),
                                                "oppentionContent": option.get("oppentionContent", ""),
                                                "isTrue": option.get("isTrue", False),
                                                "oppentionOrder": option.get("oppotionOrder", 0)
                                            }
                                            question_data["options"].append(option_data)
                            
                            knowledge_data["questions"].append(question_data)
                    
                    chapter_data["knowledges"].append(knowledge_data)
                
                course_data["chapters"].append(chapter_data)
            
            data["courses"].append(course_data)
        
        # 生成文件名
        if filename is None:
            class_name = class_info.get("className", "").replace(" ", "_")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{class_name}_all_courses_{timestamp}.json"
        
        return self.export_to_json(data, filename)

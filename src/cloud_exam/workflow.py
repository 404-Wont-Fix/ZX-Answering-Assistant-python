"""
ZX Answering Assistant - 云考试工作流程

实现云考试的核心业务逻辑，包括：
- 网络请求监听和试卷捕获
- 试卷数据解析
- 题库验证和匹配
- 答案注入流程
"""

import json
import logging
import time
import threading
from typing import Optional, Dict, List, Callable
from urllib.parse import urlparse, parse_qs

from src.cloud_exam.models import ExamPaper, ExamQuestion, QuestionOption
from src.cloud_exam.api_client import CloudExamAPIClient

logger = logging.getLogger(__name__)


class NetworkMonitor:
    """网络请求监听器"""

    def __init__(self, target_pattern: str = "*GetQuestionsByExpId*", log_callback=None):
        """
        初始化监听器

        Args:
            target_pattern: 目标URL模式
            log_callback: 日志回调函数
        """
        self.target_pattern = target_pattern
        self._log_callback = log_callback
        self.captured_requests = []
        self.captured_responses = {}
        self._is_monitoring = False
        self._lock = threading.Lock()

    def _log(self, message: str):
        """输出日志"""
        if self._log_callback:
            self._log_callback(message)
        else:
            logger.info(message)

    def start(self, page):
        """
        启动网络监听

        Args:
            page: Playwright页面对象
        """
        def handle_route(route, request):
            """处理路由"""
            if self.target_pattern in request.url:
                with self._lock:
                    self.captured_requests.append({
                        'url': request.url,
                        'method': request.method,
                        'headers': request.headers
                    })
                self._log(f"🔍 捕获目标请求: {request.url[:80]}...")
            route.continue_()

        def handle_response(response):
            """处理响应"""
            if self.target_pattern in response.url:
                try:
                    data = response.json()
                    with self._lock:
                        self.captured_responses[response.url] = data
                    self._log(f"✅ 捕获响应数据: {response.url[:60]}...")
                except Exception:
                    pass

        # 注册监听器
        page.route('**/*', handle_route)
        page.on('response', handle_response)
        self._is_monitoring = True
        self._log("🎯 网络监听器已启动")

    def get_exp_id(self) -> Optional[str]:
        """
        从捕获的请求中提取expID

        Returns:
            Optional[str]: exp_id或None
        """
        with self._lock:
            for request in self.captured_requests:
                if 'expID=' in request['url'] or 'expid=' in request['url'].lower():
                    try:
                        parsed = urlparse(request['url'])
                        params = parse_qs(parsed.query)
                        # 尝试多种可能的参数名
                        exp_id = (params.get('expID', [None])[0] or
                                  params.get('expid', [None])[0] or
                                  params.get('ExpID', [None])[0])
                        if exp_id:
                            self._log(f"📋 提取到考试ID: {exp_id[:16]}...")
                            return exp_id
                    except Exception as e:
                        logger.debug(f"解析expID失败: {e}")
        return None

    def get_exam_data(self) -> Optional[Dict]:
        """
        获取捕获的试卷数据

        Returns:
            Optional[Dict]: 试卷数据或None
        """
        with self._lock:
            if not self.captured_responses:
                return None
            # 返回第一个匹配的响应数据
            return next(iter(self.captured_responses.values()), None)

    def has_captured(self) -> bool:
        """
        检查是否已捕获到数据

        Returns:
            bool: 是否已捕获
        """
        with self._lock:
            return len(self.captured_responses) > 0

    def stop(self):
        """停止监听"""
        self._is_monitoring = False
        self._log("🛑 网络监听器已停止")

    def clear(self):
        """清除捕获的数据"""
        with self._lock:
            self.captured_requests.clear()
            self.captured_responses.clear()


class CloudExamWorkflow:
    """云考试工作流程引擎"""

    def __init__(self, log_callback=None, progress_callback=None):
        """
        初始化工作流程

        Args:
            log_callback: 日志回调函数
            progress_callback: 进度回调函数 (current, total, message)
        """
        self.log_callback = log_callback
        self.progress_callback = progress_callback

        # 状态数据
        self.access_token = None
        self.network_monitor = None
        self.exam_paper = None
        self.question_bank_data = None

    def _log(self, message: str, level: str = "info"):
        """输出日志"""
        if self.log_callback:
            self.log_callback(message)
        else:
            if level == "info":
                logger.info(message)
            elif level == "error":
                logger.error(message)
            elif level == "warning":
                logger.warning(message)
            elif level == "success":
                logger.info(f"✅ {message}")

    def _update_progress(self, current: int, total: int, message: str = ""):
        """更新进度"""
        if self.progress_callback:
            self.progress_callback(current, total, message)

    def get_student_access_token(self, skip_prompt: bool = False) -> Optional[str]:
        """
        获取学生端access_token并启动网络监听

        Args:
            skip_prompt: 是否跳过交互式提示（GUI模式使用True）

        Returns:
            Optional[str]: access_token或None
        """
        try:
            from src.auth.student import get_cached_access_token
            from src.core.browser import get_browser_manager, BrowserType

            # 尝试获取缓存的token
            self._log("🔑 检查缓存的access_token...")
            access_token = get_cached_access_token()

            if access_token:
                self._log("✅ 使用缓存的access_token", "success")
                self.access_token = access_token

                # 启动网络监听器
                manager = get_browser_manager()
                page = manager.get_page(BrowserType.STUDENT)

                if page:
                    self.network_monitor = NetworkMonitor(log_callback=self._log)
                    self.network_monitor.start(page)
                    self._log("🎯 网络监听器已启动，等待进入考试页面...")
                else:
                    self._log("⚠️ 未找到浏览器页面，请先登录学生端", "warning")

                return access_token
            else:
                self._log("❌ 未找到有效的access_token，请先登录学生端", "error")
                return None

        except Exception as e:
            self._log(f"❌ 获取access_token失败: {str(e)}", "error")
            return None

    def wait_for_exam_api(self, timeout: int = 300) -> Optional[str]:
        """
        等待捕获试卷API（阻塞直到捕获或超时）

        Args:
            timeout: 超时时间（秒），默认5分钟

        Returns:
            Optional[str]: exp_id或None
        """
        if not self.network_monitor:
            self._log("❌ 网络监听器未启动", "error")
            return None

        self._log("⏳ 请在浏览器中进入云考试页面...")
        self._log("💡 系统将自动捕获试卷数据")

        start_time = time.time()

        while time.time() - start_time < timeout:
            if self.network_monitor.has_captured():
                exp_id = self.network_monitor.get_exp_id()
                if exp_id:
                    self._log(f"✅ 成功捕获考试ID: {exp_id[:16]}...", "success")
                    return exp_id

            time.sleep(1)

        self._log("❌ 等待超时，未能捕获试卷数据", "error")
        self._log("💡 请确保：", "warning")
        self._log("   1. 已成功登录学生端")
        self._log("   2. 已在浏览器中打开云考试页面")
        self._log("   3. 页面已完全加载")
        return None

    def capture_exam_paper(self, exp_id: str) -> Optional[ExamPaper]:
        """
        获取试卷数据（直接通过API）

        Args:
            exp_id: 考试ID

        Returns:
            Optional[ExamPaper]: 试卷对象或None
        """
        try:
            self._log(f"📡 正在获取试卷数据...")
            self._log(f"   考试ID: {exp_id[:16]}...")

            if not self.access_token:
                self._log("❌ 缺少access_token", "error")
                return None

            # 直接通过API获取试卷数据
            api_client = CloudExamAPIClient(self.access_token, log_callback=self._log)
            exam_data = api_client.get_exam_paper(exp_id)

            if not exam_data:
                return None

            # 解析试卷数据
            return self._parse_exam_paper(exp_id, exam_data)

        except Exception as e:
            self._log(f"❌ 解析试卷失败: {str(e)}", "error")
            return None

    def _parse_exam_paper(self, exp_id: str, exam_data: Dict) -> Optional[ExamPaper]:
        """
        解析试卷数据

        Args:
            exp_id: 考试ID
            exam_data: API响应数据

        Returns:
            Optional[ExamPaper]: 试卷对象或None
        """
        try:
            if exam_data.get("code") != 0 or "data" not in exam_data:
                self._log(f"❌ API返回格式错误", "error")
                return None

            data = exam_data["data"]
            # 注意拼写：questiionList（3个i）
            questions_list = data.get("questiionList", [])

            if not questions_list:
                self._log("❌ 试卷中没有题目", "error")
                return None

            # 创建试卷对象
            exam_paper = ExamPaper(
                exp_id=exp_id,
                questions=[],
                raw_data=exam_data
            )

            # 解析每道题目
            for q_data in questions_list:
                question = ExamQuestion(
                    question_id=q_data.get("id", ""),
                    question_title=q_data.get("questionTitle", "").strip(),
                    question_type=q_data.get("questionsType", 0),
                    difficulty=q_data.get("difficulty", 0),
                    score=q_data.get("score", 0.0),
                )

                # 解析选项
                for opt_data in q_data.get("questionAnswer", []):
                    option = QuestionOption(
                        option_id=opt_data.get("id", ""),
                        option_content=opt_data.get("oppentionContent", "").strip(),
                        is_correct=False,  # 初始不标记正确答案（需要从题库获取）
                        option_order=opt_data.get("oppentionOrder", 0)
                    )
                    question.options.append(option)

                exam_paper.questions.append(question)

            self.exam_paper = exam_paper

            self._log(f"✅ 成功解析试卷:", "success")
            self._log(f"   考试ID: {exp_id[:16]}...")
            self._log(f"   题目数量: {len(exam_paper.questions)}")

            return exam_paper

        except Exception as e:
            self._log(f"❌ 解析试卷数据异常: {str(e)}", "error")
            return None

    def load_question_bank(self, file_path: str) -> bool:
        """
        加载题库文件

        Args:
            file_path: JSON文件路径

        Returns:
            bool: 是否成功
        """
        try:
            from src.extraction.importer import QuestionBankImporter

            self._log(f"📚 正在加载题库: {file_path}")

            importer = QuestionBankImporter()
            success = importer.import_from_file(file_path)

            if not success:
                self._log("❌ 题库文件导入失败", "error")
                return False

            # 保存题库数据
            self.question_bank_data = importer.data

            # 显示题库信息
            bank_type = importer.get_bank_type()
            if bank_type == "single":
                parsed = importer.parse_single_course()
                stats = parsed.get("statistics", {})
                self._log(f"✅ 题库加载成功:", "success")
                self._log(f"   类型: 单课程题库")
                self._log(f"   课程: {parsed.get('course', {}).get('courseName', '未知')}")
                self._log(f"   章节数: {stats.get('totalChapters', 0)}")
                self._log(f"   知识点数: {stats.get('totalKnowledges', 0)}")
                self._log(f"   题目数: {stats.get('totalQuestions', 0)}")
            elif bank_type == "multiple":
                parsed = importer.parse_multiple_courses()
                stats = parsed.get("statistics", {})
                self._log(f"✅ 题库加载成功:", "success")
                self._log(f"   类型: 多课程题库")
                self._log(f"   课程数: {stats.get('totalCourses', 0)}")
                self._log(f"   题目数: {stats.get('totalQuestions', 0)}")
            else:
                self._log("⚠️ 未知的题库类型", "warning")

            return True

        except Exception as e:
            self._log(f"❌ 加载题库异常: {str(e)}", "error")
            return False

    def validate_question_bank(self, exam_paper: ExamPaper = None) -> Dict[str, any]:
        """
        验证题库是否匹配当前考试

        Args:
            exam_paper: 试卷对象（可选，默认使用self.exam_paper）

        Returns:
            Dict: 验证结果
            {
                'valid': bool,           # 是否验证通过
                'match_rate': float,     # 匹配率（0-1）
                'matched_count': int,    # 匹配的题目数
                'total_count': int       # 总题目数
            }
        """
        if not self.question_bank_data:
            return {
                'valid': False,
                'match_rate': 0.0,
                'matched_count': 0,
                'total_count': 0
            }

        exam_paper = exam_paper or self.exam_paper
        if not exam_paper:
            return {
                'valid': False,
                'match_rate': 0.0,
                'matched_count': 0,
                'total_count': 0
            }

        self._log("🔍 正在验证题库...")

        # 统计匹配的题目数
        matched_count = 0
        total_count = len(exam_paper.questions)

        for question in exam_paper.questions:
            # 在题库中查找题目
            answer_ids = self._find_answer_in_bank(question.question_id)
            if answer_ids:
                matched_count += 1
                # 标记正确答案
                for option in question.options:
                    if option.option_id in answer_ids:
                        option.is_correct = True

        match_rate = matched_count / total_count if total_count > 0 else 0.0

        self._log(f"📊 题库验证结果:", "info")
        self._log(f"   匹配题目: {matched_count}/{total_count}")
        self._log(f"   匹配率: {match_rate:.1%}")

        # 判断是否通过验证（匹配率≥30%认为通过）
        valid = match_rate >= 0.3

        if valid:
            self._log(f"✅ 题库验证通过", "success")
        else:
            self._log(f"⚠️ 题库匹配率较低，可能不是对应的题库", "warning")

        return {
            'valid': valid,
            'match_rate': match_rate,
            'matched_count': matched_count,
            'total_count': total_count
        }

    def _find_answer_in_bank(self, question_id: str) -> Optional[List[str]]:
        """
        在题库中查找题目的答案ID

        Args:
            question_id: 题目ID

        Returns:
            Optional[List[str]]: 正确答案的ID列表，如果未找到则返回None
        """
        if not self.question_bank_data:
            return None

        try:
            # 遍历题库查找匹配的题目
            chapters = []
            if "class" in self.question_bank_data and "course" in self.question_bank_data["class"]:
                chapters = self.question_bank_data["class"]["course"].get("chapters", [])
            elif "chapters" in self.question_bank_data:
                chapters = self.question_bank_data["chapters"]

            for chapter in chapters:
                for knowledge in chapter.get("knowledges", []):
                    for bank_question in knowledge.get("questions", []):
                        # 检查题目ID是否匹配
                        if bank_question.get("QuestionID") == question_id:
                            # 获取正确答案的ID
                            answer_ids = []
                            for opt in bank_question.get("options", []):
                                if opt.get("isTrue"):
                                    answer_ids.append(opt.get("id", ""))

                            if answer_ids:
                                return answer_ids

            return None

        except Exception as e:
            logger.debug(f"查找题库失败: {e}")
            return None

    def inject_answers(self, exam_member_id: str = None) -> Dict[str, int]:
        """
        执行答案注入

        Args:
            exam_member_id: 考试成员ID（可选，如果不提供则尝试从试卷中获取）

            ⚠️ TODO: exam_member_id 参数的获取方式尚不明确（答案注入功能未完成）
            - 该参数是提交答案所必需的，但当前不知道如何从哪里获取
            - 可能需要从以下位置之一获取：
              * 考试页面的某个API响应
              * 浏览器本地存储（localStorage/sessionStorage）
              * 页面DOM元素
              * 某个Cookie
            - 当前状态：功能已实现但无法测试，需要等待网站开放后分析
            - 确定获取方式后需要更新此方法的实现

        Returns:
            Dict[str, int]: 注入结果统计
            {
                'total': int,      # 总题数
                'success': int,    # 成功提交数
                'failed': int,     # 失败数
                'skipped': int     # 跳过数
            }
        """
        if not self.exam_paper:
            self._log("❌ 请先获取试卷", "error")
            return {'total': 0, 'success': 0, 'failed': 0, 'skipped': 0}

        if not self.question_bank_data:
            self._log("❌ 请先加载题库", "error")
            return {'total': 0, 'success': 0, 'failed': 0, 'skipped': 0}

        if not self.access_token:
            self._log("❌ 缺少access_token", "error")
            return {'total': 0, 'success': 0, 'failed': 0, 'skipped': 0}

        # 验证题库
        validation = self.validate_question_bank()
        if not validation['valid'] and validation['match_rate'] < 0.1:
            self._log("❌ 题库完全不匹配，无法继续", "error")
            return {'total': 0, 'success': 0, 'failed': 0, 'skipped': 0}

        # 构建答案映射
        answer_map = {}
        for question in self.exam_paper.questions:
            answer_ids = self._find_answer_in_bank(question.question_id)
            if answer_ids:
                # 单选题，取第一个答案
                answer_map[question.question_id] = answer_ids[0]

        if not answer_map:
            self._log("❌ 题库中没有找到任何匹配的答案", "error")
            return {'total': 0, 'success': 0, 'failed': 0, 'skipped': 0}

        self._log(f"📝 准备提交 {len(answer_map)} 个答案...")

        # 获取已提交的答案列表
        api_client = CloudExamAPIClient(self.access_token, log_callback=self._log)
        submitted_answers = api_client.get_student_answer_list(self.exam_paper.exp_id)

        if submitted_answers is not None:
            # 标记已答题的题目
            for question in self.exam_paper.questions:
                if question.question_id in submitted_answers:
                    question.is_answered = True
                    question.student_answer_id = submitted_answers[question.question_id]

            self._log(f"📋 已提交: {self.exam_paper.get_answered_questions_count()}/{self.exam_paper.get_total_questions_count()}")

        # 批量提交答案
        result = api_client.submit_all_answers(
            self.exam_paper,
            answer_map,
            exam_member_id or ""
        )

        return result

    def cleanup(self):
        """清理资源"""
        if self.network_monitor:
            self.network_monitor.stop()
            self.network_monitor = None

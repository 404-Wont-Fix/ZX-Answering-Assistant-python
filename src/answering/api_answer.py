"""
API自动做题模块（暴力模式）
使用API直接构造请求来完成做题，不使用浏览器自动化
"""

import hmac
import hashlib
import json
import logging
import time
import threading
import requests
import keyboard
from typing import Dict, List, Optional
from urllib.parse import urlencode, quote

logger = logging.getLogger(__name__)


class APIAutoAnswer:
    """API自动做题类（暴力模式）"""

    # 签名密钥
    SIGN_KEY = "2fa7a73c-66d4-11f0-8925-fa163e54f941"

    # API基础URL
    BASE_URL = "https://ai.cqzuxia.com/evaluation/api"

    def __init__(self, access_token: str, log_callback=None):
        """
        初始化API自动做题器

        Args:
            access_token: 学生端access_token
            log_callback: 日志回调函数（可选），用于将日志输出到GUI
        """
        self.access_token = access_token
        self.question_bank = None  # 题库数据
        self.course_id = None  # 课程ID
        self.chapter_id = None  # 章节ID
        self.knowledge_id = None  # 知识点ID

        # 停止控制相关
        self._stop_requested = False  # 用户是否请求停止
        self._stop_thread = None  # 停止监听线程
        self._is_answering_question = False  # 是否正在答题
        self._is_processing_knowledge = False  # 是否正在处理知识点

        # 日志回调
        self._log_callback = log_callback

        # 设置日志处理器
        self._setup_log_handler()

    def _setup_log_handler(self):
        """设置日志处理器，将日志转发到回调函数"""
        if self._log_callback:
            # 创建自定义日志处理器
            class CallbackHandler(logging.Handler):
                def __init__(self, callback):
                    super().__init__()
                    self.callback = callback

                def emit(self, record):
                    try:
                        msg = self.format(record)
                        # 移除时间戳和日志级别，只保留消息内容
                        # 格式通常是：2026-01-20 20:06:11,730 - src.api_auto_answer - INFO - message
                        parts = msg.split(" - ")
                        if len(parts) >= 4:
                            message = " - ".join(parts[3:])  # 只取消息部分
                        else:
                            message = msg
                        self.callback(message.rstrip())
                    except Exception:
                        pass

            # 添加处理器到 logger
            self._log_handler = CallbackHandler(self._log_callback)
            self._log_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
            logger.addHandler(self._log_handler)

    def _cleanup_log_handler(self):
        """清理日志处理器"""
        if hasattr(self, '_log_handler') and self._log_handler:
            logger.removeHandler(self._log_handler)

    def start_stop_listener(self):
        """启动停止监听器（监听Q键）"""
        self._stop_requested = False
        self._stop_thread = threading.Thread(target=self._listen_for_stop, daemon=True)
        self._stop_thread.start()
        logger.info("✅ 停止监听器已启动（按Q键退出）")

    def _listen_for_stop(self):
        """监听停止信号的线程函数"""
        while not self._stop_requested:
            if keyboard.is_pressed('q'):
                logger.info("\n🛑 检测到Q键，准备停止...")
                self.request_stop()
                break
            time.sleep(0.1)

    def request_stop(self):
        """请求停止（按Q键时调用）"""
        self._stop_requested = True
        if self._is_answering_question:
            logger.info("⏳ 当前正在答题，完成后将停止...")
        elif self._is_processing_knowledge:
            logger.info("⏳ 当前正在处理知识点，完成后将停止...")
        else:
            logger.info("🛑 立即停止...")

    def stop_listener(self):
        """停止监听器"""
        self._stop_requested = True
        if self._stop_thread and self._stop_thread.is_alive():
            self._stop_thread.join(timeout=1)
        logger.info("🛑 停止监听器已关闭")
        # 清理日志处理器
        self._cleanup_log_handler()

    def _check_stop(self) -> bool:
        """
        检查是否应该停止

        Returns:
            bool: True表示应该停止，False表示继续
        """
        if self._stop_requested:
            # 如果正在答题，不等当前题目做完
            # 如果正在处理知识点，等当前知识点做完
            if self._is_answering_question:
                logger.info("⏸️ 等待当前题目完成...")
                return False
            elif self._is_processing_knowledge:
                logger.info("⏸️ 等待当前知识点完成...")
                return False
            else:
                logger.info("🛑 按Q键退出，停止做题")
                return True
        return False

    def _retry_request(self, func, *args, max_retries=3, delay=2, **kwargs):
        """
        重试请求装饰器

        Args:
            func: 要执行的函数
            *args: 函数参数
            max_retries: 最大重试次数
            delay: 重试延迟（秒）
            **kwargs: 函数关键字参数

        Returns:
            函数返回值，如果全部失败则返回None
        """
        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_str = str(e)
                # 检查是否是网络连接错误
                is_network_error = (
                    "ConnectionResetError" in error_str or
                    "Connection aborted" in error_str or
                    "远程主机" in error_str or
                    "10054" in error_str
                )

                if is_network_error and attempt < max_retries - 1:
                    logger.warning(f"⚠️ 网络错误，第 {attempt + 1}/{max_retries} 次尝试失败，{delay}秒后重试...")
                    time.sleep(delay)
                    continue
                else:
                    # 如果不是网络错误或已达到最大重试次数，抛出异常
                    raise e
        return None

    def load_question_bank(self, question_bank_data: Dict):
        """
        加载题库数据

        Args:
            question_bank_data: 题库数据（从JSON文件导入）
        """
        self.question_bank = question_bank_data
        logger.info("✅ 题库数据已加载")

    @staticmethod
    def generate_sign(params: str) -> str:
        """
        生成签名

        Args:
            params: 参数字符串（URL编码后的查询字符串，如 "kpid=xxx&questions=..."）

        Returns:
            str: 十六进制小写签名字符串
        """
        # 使用HMAC-SHA256生成签名
        signature = hmac.new(
            APIAutoAnswer.SIGN_KEY.encode('utf-8'),
            params.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

        return signature

    def _get_headers(self) -> Dict:
        """
        获取请求头

        Returns:
            Dict: 请求头字典
        """
        return {
            "accept": "application/json, text/plain, */*",
            "accept-language": "zh-CN,zh;q=0.9",
            "authorization": f"Bearer {self.access_token}",
            "content-type": "application/json;charset=UTF-8",
            "origin": "https://ai.cqzuxia.com",
            "referer": "https://ai.cqzuxia.com/",
            "sec-ch-ua": '"Chromium";v="138", "Not)A;Brand";v="8"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36"
        }

    def get_course_list(self) -> Optional[List[Dict]]:
        """
        获取课程列表（第一步）

        Returns:
            Optional[List[Dict]]: 课程列表，如果失败则返回None
        """
        try:
            from src.core.api_client import get_api_client

            logger.info("📋 获取课程列表...")

            url = f"{self.BASE_URL}/StudentEvaluate/GetCourseList"
            headers = self._get_headers()

            api_client = get_api_client()
            response = api_client.get(url, headers=headers)

            if response is None:
                return None

            if response.status_code == 200:
                data = response.json()
                logger.info(f"✅ 成功获取课程列表")
                return data
            else:
                logger.error(f"❌ 获取课程列表失败: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"❌ 获取课程列表异常: {str(e)}")
            return None

    def get_course_info(self, course_id: str) -> Optional[Dict]:
        """
        获取课程详细信息（用于检查知识点状态）

        Args:
            course_id: 课程ID

        Returns:
            Optional[Dict]: 课程信息，包含知识点的完成状态，如果失败则返回None
        """
        try:
            from src.core.api_client import get_api_client

            logger.info(f"📋 获取课程 {course_id} 的详细信息...")

            url = f"{self.BASE_URL}/studentevaluate/GetCourseInfoByCourseId?CourseID={course_id}"
            headers = self._get_headers()

            api_client = get_api_client()
            response = api_client.get(url, headers=headers)

            if response is None:
                return None

            if response.status_code == 200:
                data = response.json()
                if data.get("success") and "data" in data:
                    logger.info(f"✅ 成功获取课程详细信息")
                    logger.debug(f"   数据类型: {type(data['data'])}")
                    # 如果是列表且不为空，记录第一个元素的结构
                    if isinstance(data["data"], list) and len(data["data"]) > 0:
                        logger.debug(f"   数据长度: {len(data['data'])}")
                        logger.debug(f"   第一个元素keys: {list(data['data'][0].keys()) if isinstance(data['data'][0], dict) else 'not a dict'}")
                    return data["data"]
                else:
                    logger.error(f"❌ API返回错误: {data}")
                    return None
            else:
                logger.error(f"❌ 获取课程信息失败: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"❌ 获取课程信息异常: {str(e)}")
            return None

    def get_chapter_and_knowledge(self, course_id: str) -> Optional[Dict]:
        """
        获取课程的章节和知识点信息（第一步）

        Args:
            course_id: 课程ID

        Returns:
            Optional[Dict]: 包含章节和知识点信息的字典，如果失败则返回None
        """
        try:
            from src.core.api_client import get_api_client

            logger.info(f"📖 获取课程 {course_id} 的章节和知识点信息...")

            # 获取未完成的章节列表
            url = f"{self.BASE_URL}/StuEvaluateReport/GetUnCompleteChapterList?CourseID={course_id}"
            headers = self._get_headers()

            api_client = get_api_client()
            response = api_client.get(url, headers=headers)

            if response is None:
                return None

            if response.status_code == 200:
                data = response.json()
                if data.get("success") and "data" in data:
                    chapters_data = data["data"]
                    logger.info(f"✅ 成功获取章节和知识点信息，共 {len(chapters_data)} 个章节")
                    return chapters_data
                else:
                    logger.error(f"❌ API返回错误: {data}")
                    return None
            else:
                logger.error(f"❌ 获取章节信息失败: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"❌ 获取章节信息异常: {str(e)}")
            return None

    def _begin_evaluate_request(self, kpid: str) -> Optional[Dict]:
        """
        开始测评的实际请求逻辑（内部方法，用于重试）

        Args:
            kpid: 知识点ID

        Returns:
            Optional[Dict]: 包含题目列表的响应数据，如果失败则返回None
                     如果返回特殊字符串"skip"，表示需要跳过该知识点
        """
        try:
            from src.core.api_client import get_api_client

            # 构造参数字符串（用于签名，不编码）
            params_raw = f"kpid={kpid}"

            # 生成签名（基于未编码的参数字符串）
            sign = self.generate_sign(params_raw)

            # 构造URL参数（需要URL编码）
            params_encoded = urlencode({"kpid": kpid, "sign": sign})
            url = f"{self.BASE_URL}/studentevaluate/beginevaluate?{params_encoded}"

            headers = self._get_headers()

            logger.info(f"   签名原文: {params_raw}")
            logger.info(f"   签名结果: {sign[:16]}...")
            logger.info(f"   请求URL: {url}")

            api_client = get_api_client()
            response = api_client.get(url, headers=headers)

            if response is None:
                return None

            if response.status_code == 200:
                data = response.json()
                if data.get("code") == 0 and "data" in data:
                    question_list = data["data"].get("questionList", [])
                    logger.info(f"✅ 成功开始测评，共 {len(question_list)} 道题")
                    return data["data"]
                else:
                    error_msg = data.get("msg", "")
                    # 检查是否是次数用尽的错误
                    if "评估过3次" in error_msg or "已经评估" in error_msg:
                        logger.warning(f"⚠️ 该知识点已完成或次数已用尽: {error_msg}")
                        return "skip"  # 返回特殊标记表示需要跳过
                    logger.error(f"❌ API返回错误: {data}")
                    return None
            else:
                logger.error(f"❌ 开始测评失败: {response.status_code}")
                logger.error(f"   响应内容: {response.text[:500]}")
                return None

        except Exception as e:
            logger.error(f"❌ 开始测评异常: {str(e)}")
            return None

    def begin_evaluate(self, kpid: str) -> Optional[Dict]:
        """
        开始测评（第二步，带重试）

        Args:
            kpid: 知识点ID

        Returns:
            Optional[Dict]: 包含题目列表的响应数据，如果失败则返回None
                     如果返回特殊字符串"skip"，表示需要跳过该知识点
        """
        try:
            logger.info(f"🚀 开始测评知识点: {kpid}")
            return self._retry_request(self._begin_evaluate_request, kpid)
        except Exception as e:
            logger.error(f"❌ 开始测评异常（重试后仍失败）: {str(e)}")
            return None

    def _save_evaluate_answer_request(self, kpid: str, question_id: str, answer_id: str) -> bool:
        """
        保存单道题答案的实际请求逻辑（内部方法，用于重试）

        Args:
            kpid: 知识点ID
            question_id: 题目ID
            answer_id: 答案ID（多选题用逗号分隔，如 "id1,id2"）

        Returns:
            bool: 是否成功保存
        """
        try:
            from src.core.api_client import get_api_client

            # 构造请求体中的questions数组（使用大写字段名）
            questions_data = [{"QuestionID": question_id, "AnswerID": answer_id}]

            # 签名时使用小写字段名（注意：签名原文和请求体的字段名大小写不同！）
            # 签名原文格式：kpid=xxx&questions=[{"questionid":"...","answerid":"..."}]
            questions_for_sign = [{"questionid": question_id, "answerid": answer_id}]
            questions_json = json.dumps(questions_for_sign, separators=(',', ':'), ensure_ascii=False)

            params_raw = f"kpid={kpid}&questions={questions_json}"

            # 生成签名（基于未编码的参数字符串）
            sign = self.generate_sign(params_raw)

            # 构造请求URL
            url = f"{self.BASE_URL}/StudentEvaluate/SaveEvaluateAnswer"

            # 构造请求体
            body = {
                "kpid": kpid,
                "questions": questions_data,
                "sign": sign
            }
            headers = self._get_headers()

            logger.info(f"   === SaveEvaluateAnswer 请求详情 ===")
            logger.info(f"   签名原文: {params_raw}")
            logger.info(f"   签名结果: {sign}")
            logger.info(f"   请求URL: {url}")
            logger.info(f"   请求体: {json.dumps(body, ensure_ascii=False, separators=(',', ':'))}")
            logger.info(f"   ===============================")

            api_client = get_api_client()
            response = api_client.post(url, json=body, headers=headers)

            if response is None:
                return False

            if response.status_code == 200:
                data = response.json()
                if data.get("code") == 0 or data.get("success"):
                    logger.info(f"   ✅ 已保存答案")
                    return True
                else:
                    logger.error(f"❌ API返回错误: {data}")
                    return False
            else:
                logger.error(f"❌ 保存答案失败: {response.status_code}")
                logger.error(f"   响应内容: {response.text[:500]}")
                return False

        except Exception as e:
            logger.error(f"❌ 保存答案异常: {str(e)}")
            return False

    def save_evaluate_answer(self, kpid: str, question_id: str, answer_id: str) -> bool:
        """
        保存单道题的答案（第三步，带重试）

        Args:
            kpid: 知识点ID
            question_id: 题目ID
            answer_id: 答案ID（多选题用逗号分隔，如 "id1,id2"）

        Returns:
            bool: 是否成功保存
        """
        try:
            return self._retry_request(self._save_evaluate_answer_request, kpid, question_id, answer_id)
        except Exception as e:
            logger.error(f"❌ 保存答案异常（重试后仍失败）: {str(e)}")
            return False

    def _save_test_member_info_request(self, kpid: str) -> bool:
        """
        保存评估信息的实际请求逻辑（内部方法，用于重试）

        Args:
            kpid: 知识点ID

        Returns:
            bool: 是否成功保存
        """
        try:
            from src.core.api_client import get_api_client

            # 构造questions JSON字符串（空数组，表示已完成）
            questions_json = "[]"

            # 构造参数字符串（用于签名，不编码）
            # 原文：kpid=xxx&questions=[]
            params_raw = f"kpid={kpid}&questions={questions_json}"

            # 生成签名（基于未编码的参数字符串）
            sign = self.generate_sign(params_raw)

            # 构造请求URL（无参数）
            url = f"{self.BASE_URL}/StudentEvaluate/SaveTestMemberInfo"

            # 构造请求体（包含kpid、questions和sign）
            body = {
                "kpid": kpid,
                "questions": [],
                "sign": sign
            }
            headers = self._get_headers()

            logger.info(f"   签名原文: {params_raw}")
            logger.info(f"   签名结果: {sign[:16]}...")
            logger.info(f"   请求URL: {url}")
            logger.info(f"   请求体JSON: {json.dumps(body, ensure_ascii=False, separators=(',', ':'))}")

            api_client = get_api_client()
            response = api_client.post(url, json=body, headers=headers)

            if response is None:
                return False

            if response.status_code == 200:
                data = response.json()
                if data.get("code") == 0 or data.get("success"):
                    logger.info(f"✅ 成功提交试卷")
                    return True
                else:
                    logger.error(f"❌ API返回错误: {data}")
                    return False
            else:
                logger.error(f"❌ 提交试卷失败: {response.status_code}")
                logger.error(f"   响应内容: {response.text[:500]}")
                return False

        except Exception as e:
            logger.error(f"❌ 提交试卷异常: {str(e)}")
            return False

    def save_test_member_info(self, kpid: str) -> bool:
        """
        保存评估信息（第四步，提交试卷，带重试）

        Args:
            kpid: 知识点ID

        Returns:
            bool: 是否成功保存
        """
        try:
            logger.info(f"📝 提交试卷...")
            return self._retry_request(self._save_test_member_info_request, kpid)
        except Exception as e:
            logger.error(f"❌ 提交试卷异常（重试后仍失败）: {str(e)}")
            return False

    def find_answer_in_bank(self, question_id: str) -> Optional[List[str]]:
        """
        在题库中查找题目的答案ID

        Args:
            question_id: 题目ID

        Returns:
            Optional[List[str]]: 正确答案的ID列表，如果未找到则返回None
        """
        if not self.question_bank:
            logger.warning("⚠️ 题库未加载")
            return None

        try:
            logger.info(f"🔍 在题库中查找题目ID: {question_id[:8]}...")

            # 遍历题库查找匹配的题目
            chapters = []
            if "class" in self.question_bank and "course" in self.question_bank["class"]:
                chapters = self.question_bank["class"]["course"].get("chapters", [])
            elif "chapters" in self.question_bank:
                chapters = self.question_bank["chapters"]

            for chapter in chapters:
                for knowledge in chapter.get("knowledges", []):
                    for bank_question in knowledge.get("questions", []):
                        # 检查题目ID是否匹配
                        if bank_question.get("QuestionID") == question_id:
                            logger.info(f"✅ 在题库中找到题目")

                            # 获取正确答案的ID
                            answer_ids = []
                            for opt in bank_question.get("options", []):
                                if opt.get("isTrue"):
                                    answer_ids.append(opt.get("id", ""))

                            if answer_ids:
                                logger.info(f"   正确答案ID: {answer_ids}")
                                return answer_ids
                            else:
                                logger.warning("⚠️ 题库中未标记正确答案")
                                return None

            logger.warning(f"⚠️ 题库中未找到题目ID: {question_id[:8]}...")
            return None

        except Exception as e:
            logger.error(f"❌ 查找题库失败: {str(e)}")
            return None

    def answer_knowledge(self, kpid: str) -> Dict:
        """
        完成一个知识点的答题流程

        Args:
            kpid: 知识点ID

        Returns:
            Dict: 答题结果统计
            {
                'total': int,  # 总题数
                'success': int,  # 成功题数
                'failed': int,  # 失败题数
                'skipped': int  # 跳过题数
            }
        """
        result = {
            'total': 0,
            'success': 0,
            'failed': 0,
            'skipped': 0
        }

        try:
            # 标记正在处理知识点
            self._is_processing_knowledge = True

            logger.info("=" * 60)
            logger.info(f"📚 开始处理知识点: {kpid}")
            logger.info("=" * 60)

            # 第二步：开始测评，获取题目列表
            evaluate_data = self.begin_evaluate(kpid)
            if evaluate_data == "skip":
                # 该知识点已完成或次数用尽，跳过
                logger.info(f"⏭️ 跳过该知识点（已完成或次数用尽）")
                result['skipped'] = 0  # 标记为跳过
                self._is_processing_knowledge = False
                return result
            if not evaluate_data:
                logger.error("❌ 开始测评失败")
                self._is_processing_knowledge = False
                return result

            question_list = evaluate_data.get("questionList", [])
            result['total'] = len(question_list)

            if not question_list:
                logger.warning("⚠️ 该知识点没有题目")
                self._is_processing_knowledge = False
                return result

            logger.info(f"📝 共 {len(question_list)} 道题")

            # 第三步：逐题查找答案并保存
            for idx, question in enumerate(question_list, 1):
                # 标记正在答题
                self._is_answering_question = True

                # 检查是否需要停止（在每道题开始前）
                if self._check_stop():
                    self._is_answering_question = False
                    self._is_processing_knowledge = False
                    return result

                question_id = question.get("id", "")
                question_title = question.get("questionTitle", "")[:50]

                logger.info(f"\n📌 题目 {idx}/{len(question_list)}: {question_id[:8]}... - {question_title}...")

                # 在题库中查找答案
                answer_ids = self.find_answer_in_bank(question_id)

                if answer_ids:
                    # 找到答案，立即保存
                    # 多选题的answerid用逗号分隔
                    answer_id_str = ",".join(answer_ids)
                    logger.info(f"   ✅ 找到答案: {answer_id_str[:30]}...")

                    # 调用API保存单道题答案
                    if self.save_evaluate_answer(kpid, question_id, answer_id_str):
                        result['success'] += 1
                    else:
                        result['failed'] += 1
                else:
                    # 未找到答案，跳过该题
                    result['skipped'] += 1
                    logger.warning(f"   ⚠️ 未找到答案，跳过该题")

                # 标记答题完成
                self._is_answering_question = False

                # 检查是否需要停止（每道题完成后）
                if self._check_stop():
                    self._is_processing_knowledge = False
                    return result

                # 每道题之间延迟1.5秒，避免请求过快
                if idx < len(question_list):  # 最后一道题不需要延迟
                    time.sleep(1.5)

            # 第四步：提交试卷
            logger.info(f"\n📝 提交试卷...")
            if not self.save_test_member_info(kpid):
                logger.error("❌ 提交试卷失败")
                self._is_processing_knowledge = False
                return result

            logger.info("\n" + "=" * 60)
            logger.info(f"✅ 知识点 {kpid} 答题完成")
            logger.info(f"📊 统计: 总计 {result['total']} 题, 成功 {result['success']} 题, 跳过 {result['skipped']} 题")
            logger.info("=" * 60)

            # 标记知识点处理完成
            self._is_processing_knowledge = False

            return result

        except Exception as e:
            logger.error(f"❌ 答题流程异常: {str(e)}")
            self._is_answering_question = False
            self._is_processing_knowledge = False
            return result

    def auto_answer_all_knowledges(self, course_id: str, max_knowledges: int = None) -> Dict:
        """
        自动完成课程的所有未完成知识点

        Args:
            course_id: 课程ID
            max_knowledges: 最多完成的知识点数量（实际成功完成的，不包括跳过的），None表示全部

        Returns:
            Dict: 总体统计
            {
                'total_knowledges': int,  # 总知识点数
                'completed_knowledges': int,  # 完成的知识点数
                'total_questions': int,  # 总题数
                'success': int,  # 成功题数
                'failed': int,  # 失败题数
                'skipped': int  # 跳过题数
            }
        """
        total_result = {
            'total_knowledges': 0,
            'completed_knowledges': 0,
            'skipped_knowledges': 0,  # 新增：跳过的知识点数
            'total_questions': 0,
            'success': 0,
            'failed': 0,
            'skipped': 0
        }

        # 启动停止监听器
        self.start_stop_listener()

        try:
            logger.info("🚀 开始自动完成所有知识点")
            logger.info("=" * 60)

            # 第0步：获取课程详细信息，检查知识点状态
            course_info = self.get_course_info(course_id)

            # 构建知识点状态映射表
            knowledge_status = {}  # {kpid: {"isPass": bool, "times": int}}
            if course_info:
                logger.debug(f"   课程信息类型: {type(course_info)}")
                # 处理不同的数据结构
                info_list = []
                if isinstance(course_info, list):
                    info_list = course_info
                    logger.debug(f"   课程信息是列表，长度: {len(course_info)}")
                elif isinstance(course_info, dict):
                    # 可能是嵌套结构，尝试提取知识点列表
                    logger.debug(f"   课程信息是字典，keys: {list(course_info.keys())[:5]}")
                    if "data" in course_info:
                        info_list = course_info["data"] if isinstance(course_info["data"], list) else [course_info["data"]]
                    else:
                        info_list = [course_info]
                else:
                    logger.warning(f"⚠️ 课程信息格式未知: {type(course_info)}")

                for item in info_list:
                    if not isinstance(item, dict):
                        logger.debug(f"   跳过非dict项: {type(item)}")
                        continue
                    kpid = item.get("id", "")
                    test_member_info = item.get("testMemberInfo", {})
                    is_pass = test_member_info.get("isPass", False)
                    times = test_member_info.get("times", 0)

                    if kpid:
                        knowledge_status[kpid] = {
                            "isPass": is_pass,
                            "times": times
                        }

                logger.info(f"📊 获取到 {len(knowledge_status)} 个知识点的状态信息")

            # 第一步：获取课程的章节和知识点信息
            chapters_data = self.get_chapter_and_knowledge(course_id)
            if not chapters_data:
                logger.error("❌ 获取章节信息失败")
                self.stop_listener()
                return total_result

            # 收集所有未完成的知识点
            all_knowledges = []
            skipped_count = 0  # 已完成或次数用尽的知识点数量

            for chapter in chapters_data:
                chapter_title = chapter.get('title', 'N/A')
                knowledge_list = chapter.get('knowledgeList', [])

                for knowledge in knowledge_list:
                    knowledge_id = knowledge.get('id', '')
                    knowledge_name = knowledge.get('knowledge', 'N/A')

                    # 检查知识点状态
                    status = knowledge_status.get(knowledge_id, {})
                    is_pass = status.get("isPass", False)
                    times = status.get("times", 0)

                    # 如果已完成或次数已达3次，跳过
                    if is_pass or times >= 3:
                        skipped_count += 1
                        logger.info(f"⏭️ 跳过知识点: {knowledge_name} (已完成: {is_pass}, 已做次数: {times})")
                        continue

                    all_knowledges.append({
                        'kpid': knowledge_id,
                        'chapter': chapter_title,
                        'knowledge': knowledge_name
                    })

            total_result['total_knowledges'] = len(all_knowledges) + skipped_count
            # 将预检查跳过的知识点数加到最终统计中
            total_result['skipped_knowledges'] = skipped_count

            if not all_knowledges:
                logger.info("✅ 没有未完成的知识点")
                self.stop_listener()
                return total_result

            logger.info(f"📋 共找到 {len(all_knowledges)} 个未完成的知识点")

            # 确定实际需要处理的知识点数量
            # 如果指定了max_knowledges，则处理直到成功完成指定数量（跳过的不计入）
            target_count = max_knowledges if max_knowledges else len(all_knowledges)

            if max_knowledges:
                logger.info(f"⏳ 目标: 成功完成 {target_count} 个知识点（跳过的知识点不计入）")

            # 逐个处理知识点
            completed_count = 0  # 实际成功完成的数量
            processed_index = 0  # 已处理的索引

            while completed_count < target_count and processed_index < len(all_knowledges):
                # 检查是否需要停止
                if self._check_stop():
                    logger.info("🛑 按Q键退出，停止做题")
                    break

                knowledge_info = all_knowledges[processed_index]
                kpid = knowledge_info['kpid']
                chapter = knowledge_info['chapter']
                knowledge = knowledge_info['knowledge']

                print(f"\n📍 进度: 尝试 {completed_count + 1}/{target_count} (已跳过 {total_result['skipped_knowledges']} 个)")
                print(f"📖 章节: {chapter}")
                print(f"📝 知识点: {knowledge}")

                # 处理该知识点
                result = self.answer_knowledge(kpid)

                # 检查是否被跳过（result中total=0且skipped=0表示被提前跳过）
                is_skipped = (result['total'] == 0 and result['skipped'] == 0)

                if is_skipped:
                    # 该知识点被跳过（已完成或次数用尽）
                    total_result['skipped_knowledges'] += 1
                    logger.info(f"⏭️ 该知识点已跳过，继续下一个...")
                else:
                    # 该知识点已处理（无论成功或失败）
                    completed_count += 1
                    total_result['completed_knowledges'] += 1
                    total_result['total_questions'] += result['total']
                    total_result['success'] += result['success']
                    total_result['failed'] += result['failed']
                    total_result['skipped'] += result['skipped']

                processed_index += 1

                # 检查是否需要停止（每个知识点处理完后）
                if self._check_stop():
                    logger.info("🛑 按Q键退出，停止做题")
                    break

                # 延迟，避免请求过快（防止429频率限制错误）
                if completed_count < target_count and processed_index < len(all_knowledges):
                    delay = 3  # 每个知识点之间延迟3秒
                    logger.info(f"⏳ 等待 {delay} 秒后处理下一个知识点...")
                    time.sleep(delay)

            logger.info("\n" + "=" * 60)
            logger.info("🎉 所有知识点处理完成")
            logger.info("=" * 60)
            logger.info(f"📊 总体统计:")
            logger.info(f"   知识点: 已完成 {total_result['completed_knowledges']}/{total_result['total_knowledges']}, 跳过 {total_result['skipped_knowledges']} 个")
            logger.info(f"   题目: 总计 {total_result['total_questions']} 题, 成功 {total_result['success']} 题, 跳过 {total_result['skipped']} 题")
            logger.info("=" * 60)

            return total_result

        except KeyboardInterrupt:
            logger.info("\n\n⚠️ 用户中断自动做题")
            self.stop_listener()
            return total_result
        except Exception as e:
            logger.error(f"❌ 自动做题流程异常: {str(e)}")
            self.stop_listener()
            return total_result
        finally:
            # 确保停止监听器被关闭
            self.stop_listener()

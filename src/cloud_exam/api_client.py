"""
ZX Answering Assistant - 云考试API客户端

处理云考试相关的API调用
"""

import logging
import json
from typing import Optional, List, Dict

logger = logging.getLogger(__name__)


class CloudExamAPIClient:
    """云考试API客户端"""

    # API基础URL
    BASE_URL = "https://ai.cqzuxia.com/exam/api/StudentExam"

    def __init__(self, access_token: str, log_callback=None):
        """
        初始化API客户端

        Args:
            access_token: 学生端access_token
            log_callback: 日志回调函数（可选）
        """
        self.access_token = access_token
        self._log_callback = log_callback

    def _log(self, message: str, level: str = "info"):
        """输出日志"""
        if self._log_callback:
            self._log_callback(message)
        else:
            if level == "info":
                logger.info(message)
            elif level == "error":
                logger.error(message)
            elif level == "warning":
                logger.warning(message)
            elif level == "success":
                logger.info(f"✅ {message}")

    def _get_headers(self) -> Dict[str, str]:
        """
        获取请求头

        Returns:
            Dict[str, str]: 请求头字典
        """
        return {
            "accept": "application/json, text/plain, */*",
            "accept-language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
            "authorization": f"Bearer {self.access_token}",
            "content-type": "application/json;charset=UTF-8",
            "origin": "https://ai.cqzuxia.com",
            "priority": "u=1, i",
            "referer": "https://ai.cqzuxia.com/",
            "sec-ch-ua": '"Microsoft Edge";v="143", "Chromium";v="143", "Not A(Brand";v="24"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36 Edg/143.0.0.0"
        }

    def get_exam_paper(self, exp_id: str) -> Optional[Dict]:
        """
        获取试卷数据

        Args:
            exp_id: 考试ID

        Returns:
            Optional[Dict]: API响应数据，如果失败则返回None
        """
        from src.core.api_client import get_api_client

        try:
            url = f"{self.BASE_URL}/GetQuestionsByExpId?expID={exp_id}"
            headers = self._get_headers()

            self._log(f"📥 正在获取试卷: {exp_id[:16]}...")

            api_client = get_api_client()
            response = api_client.get(url, headers=headers)

            if response and response.status_code == 200:
                data = response.json()
                if data.get("code") == 0:
                    self._log(f"✅ 成功获取试卷，共 {len(data.get('data', {}).get('questiionList', []))} 道题", "success")
                    return data
                else:
                    # 特殊错误处理
                    msg = data.get("msg", "未知错误")
                    if "已交卷" in msg:
                        self._log(f"❌ {msg}", "error")
                        self._log(f"💡 该考试已完成，请选择其他未完成的考试", "warning")
                    else:
                        self._log(f"❌ API返回错误: {msg}", "error")
                    return None
            else:
                status_code = response.status_code if response else "N/A"
                self._log(f"❌ 获取试卷失败，状态码: {status_code}", "error")
                return None

        except Exception as e:
            self._log(f"❌ 获取试卷异常: {str(e)}", "error")
            return None

    def get_student_answer_list(self, exp_id: str) -> Optional[Dict[str, str]]:
        """
        获取已提交的答案列表

        Args:
            exp_id: 考试ID

        Returns:
            Optional[Dict[str, str]]: 题目ID到答案ID的映射，如果失败则返回None
                     格式: {questionID: answerID}
        """
        from src.core.api_client import get_api_client

        try:
            url = f"{self.BASE_URL}/GetStudentAnswerList?expID={exp_id}"
            headers = self._get_headers()

            self._log(f"📋 正在获取已提交答案...")

            api_client = get_api_client()
            response = api_client.get(url, headers=headers)

            if response and response.status_code == 200:
                data = response.json()
                if data.get("code") == 0 and data.get("data"):
                    # 将数组转换为字典映射
                    answer_map = {
                        item["questionID"]: item["answerID"]
                        for item in data["data"]
                    }
                    self._log(f"✅ 已获取 {len(answer_map)} 个已提交答案", "success")
                    return answer_map
                else:
                    self._log(f"⚠️ 暂无已提交答案", "warning")
                    return {}
            else:
                status_code = response.status_code if response else "N/A"
                self._log(f"❌ 获取答案列表失败，状态码: {status_code}", "error")
                return None

        except Exception as e:
            self._log(f"❌ 获取答案列表异常: {str(e)}", "error")
            return None

    def submit_answer(
        self,
        question_id: str,
        answer_id: str,
        exp_id: str,
        exam_member_id: str
    ) -> bool:
        """
        提交单题答案

        Args:
            question_id: 题目ID
            answer_id: 选项ID（答案ID）
            exp_id: 考试ID
            exam_member_id: 考试成员ID

            ⚠️ TODO: exam_member_id 参数的获取方式尚不明确
            - 该参数从哪里获取需要从实际网站分析确定
            - 可能需要从考试页面、API响应或本地存储中提取
            - 当前实现需要手动提供此参数

        Returns:
            bool: 是否提交成功
        """
        from src.core.api_client import get_api_client

        try:
            url = f"{self.BASE_URL}/StudentAnswer"
            headers = self._get_headers()

            # 构造请求体
            body = {
                "QuestionID": question_id,
                "AnswerID": answer_id,
                "ExamPapersID": exp_id,
                "ExamMemberID": exam_member_id
            }

            self._log(f"💾 提交答案: {question_id[:8]}... -> {answer_id[:8]}...")

            api_client = get_api_client()
            response = api_client.post(url, json=body, headers=headers)

            if response and response.status_code == 200:
                data = response.json()
                if data.get("code") == 0 and data.get("success"):
                    return True
                else:
                    self._log(f"❌ 提交答案失败: {data}", "error")
                    return False
            else:
                status_code = response.status_code if response else "N/A"
                self._log(f"❌ 提交答案失败，状态码: {status_code}", "error")
                return False

        except Exception as e:
            self._log(f"❌ 提交答案异常: {str(e)}", "error")
            return False

    def submit_all_answers(
        self,
        exam_paper,
        answer_map: Dict[str, str],
        exam_member_id: str
    ) -> Dict[str, int]:
        """
        批量提交答案

        Args:
            exam_paper: ExamPaper对象
            answer_map: 题目ID到答案ID的映射 {question_id: answer_id}
            exam_member_id: 考试成员ID

        Returns:
            Dict[str, int]: 提交结果统计
            {
                'total': int,      # 总题数
                'success': int,    # 成功提交数
                'failed': int,     # 失败数
                'skipped': int     # 跳过数（题库中无答案）
            }
        """
        result = {'total': 0, 'success': 0, 'failed': 0, 'skipped': 0}

        self._log("=" * 60)
        self._log("🚀 开始批量提交答案")
        self._log("=" * 60)

        for question in exam_paper.questions:
            result['total'] += 1

            # 如果已经提交过答案，跳过
            if question.is_answered:
                self._log(f"⏭️ 题目 {result['total']}: 已提交，跳过")
                result['skipped'] += 1
                continue

            # 在答案映射中查找
            answer_id = answer_map.get(question.question_id)

            if not answer_id:
                self._log(f"⚠️ 题目 {result['total']}: 未找到答案，跳过")
                result['skipped'] += 1
                continue

            # 提交答案
            if self.submit_answer(
                question.question_id,
                answer_id,
                exam_paper.exp_id,
                exam_member_id
            ):
                result['success'] += 1
                self._log(f"✅ 题目 {result['total']}: 提交成功", "success")
            else:
                result['failed'] += 1

        self._log("=" * 60)
        self._log(f"📊 提交完成: 总计 {result['total']} 题, 成功 {result['success']} 题, 失败 {result['failed']} 题, 跳过 {result['skipped']} 题")
        self._log("=" * 60)

        return result

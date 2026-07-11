"""
课程认证 API 模式做题模块

使用 API 直接进行答题，无需浏览器操作
"""

import html
import logging
import re
from typing import Dict, List, Optional
from src.core.api_client import get_api_client
from src.utils.text import normalize_text, get_chapters
from src.utils.bank_matcher import find_correct_answer_ids
from src.utils.logging import setup_callback_logging, cleanup_callback_logging
from src.core.headers import get_api_headers

# 创建模块 logger
logger = logging.getLogger(__name__)


class APICourseAnswer:
    """API模式做题器"""

    def __init__(self, access_token: str, log_callback=None):
        """
        初始化 API 做题器

        Args:
            access_token: 访问令牌
            log_callback: 日志回调函数（可选），用于将日志输出到GUI
        """
        self.access_token = access_token
        self.api_client = get_api_client()

        # API 基础 URL
        self.base_url = "https://zxsz.cqzuxia.com/teacherCertifiApi/api/TeacherCourseEvaluate"

        # 请求头
        self.headers = get_api_headers(
            "edge_144", access_token,
            referer="https://zxsz.cqzuxia.com/",
            extra_headers={
                "content-type": "application/json",
                "dnt": "1",
                "sec-gpc": "1",
                "priority": "u=1, i",
            },
        )

        # 日志回调函数
        self._log_callback = log_callback

        # 设置日志处理器
        self._setup_log_handler()

    def _setup_log_handler(self):
        """设置日志处理器，将日志输出到GUI"""
        self._log_handler = setup_callback_logging(logger, self._log_callback)

    def _cleanup_log_handler(self):
        """清理日志处理器"""
        cleanup_callback_logging(logger, self._log_handler)
        self._log_handler = None

    def _normalize_text(self, text: str) -> str:
        """标准化文本"""
        return normalize_text(text)

    def get_course_tree(self, ecourse_id: str) -> Optional[Dict]:
        """
        获取课程的知识点和章节树

        返回数据结构:
        {
            "chapterList": [
                {
                    "id": "章节ID",
                    "title": "第X章",
                    "titleContent": "章节名称",
                    "teacherKPList": [
                        {
                            "kpid": "知识点ID",
                            "knowledge": "知识点名称",
                            "isPass": true/false,  // 是否已完成
                            "questionCount": 0  // 题目数量
                        }
                    ]
                }
            ],
            "coursenName": "课程名称"
        }

        Args:
            ecourse_id: 课程ID

        Returns:
            Dict: 课程树数据，包含章节和知识点信息
        """
        url = f"{self.base_url}/GetTeacherCourseEvaluateCompleteTree?ECourseId={ecourse_id}"

        try:
            logger.info("📡 [API请求] 获取课程树...")
            response = self.api_client.get(url, headers=self.headers)

            if response is None:
                logger.error("❌ 获取课程树失败：未收到有效响应")
                return None

            if response.status_code == 200:
                data = response.json()
                if data.get('code') == 0:
                    logger.info(f"✅ [API响应] 成功 - 章节数: {len(data.get('data', {}).get('chapterList', []))}")
                    return data.get('data')
                else:
                    logger.error(f"❌ 获取课程树失败: {data.get('msg', '未知错误')}")
                    return None
            else:
                logger.error(f"❌ 获取课程树失败，状态码: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"❌ 获取课程树异常: {str(e)}")
            return None

    def get_question_list(self, kp_id: str) -> Optional[List[Dict]]:
        """
        获取知识点的题目列表

        返回数据结构:
        [
            {
                "questionID": "题目ID",
                "questionTitle": "题目内容（包含HTML实体）",
                "questionsType": 0,  # 0=单选, 1=多选
                "answerList": [
                    {
                        "answerID": "选项ID",
                        "oppentionContent": "选项内容（包含HTML实体）",
                        "oppentionOrder": 0  # 选项顺序
                    }
                ]
            }
        ]

        Args:
            kp_id: 知识点ID

        Returns:
            List[Dict]: 题目列表
        """
        url = f"{self.base_url}/GetQuesionListByKPId?kpId={kp_id}"

        try:
            logger.info(f"📡 [API请求] 获取题目列表 (kpId: {kp_id[:8]}...)")
            response = self.api_client.get(url, headers=self.headers)

            if response is None:
                logger.error("❌ 获取题目列表失败：未收到有效响应")
                return None

            if response.status_code == 200:
                data = response.json()
                if data.get('code') == 0:
                    question_list = data.get('data', [])
                    logger.info(f"✅ [API响应] 成功 - 题目数: {len(question_list)}")
                    return question_list
                else:
                    logger.error(f"❌ 获取题目列表失败: {data.get('msg', '未知错误')}")
                    return None
            else:
                logger.error(f"❌ 获取题目列表失败，状态码: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"❌ 获取题目列表异常: {str(e)}")
            return None

    def submit_answers(self, submit_data: List[Dict]) -> Optional[Dict]:
        """
        提交答案（一次性提交整个知识点的所有答案）

        请求格式:
        [
            {
                "kpid": "知识点ID",
                "questionID": "题目ID",
                "answerID": "选项ID（单选）或 'id1,id2,id3'（多选）"
            }
        ]

        响应格式:
        {
            "code": 0,
            "data": {
                "questionCount": 10,    // 总题数
                "faildCount": 1         // 失败数量（注意拼写）
            }
        }

        Args:
            submit_data: 提交数据列表

        Returns:
            Dict: 提交结果，包含 questionCount 和 faildCount，失败返回 None
        """
        url = f"{self.base_url}/SaveTeacherCourseEvaluateInfo"

        try:
            logger.info(f"📡 [API请求] 提交答案 ({len(submit_data)} 题)...")
            response = self.api_client.post(
                url,
                headers=self.headers,
                json=submit_data
            )

            if response is None:
                logger.error("❌ 提交答案失败：未收到有效响应")
                return None

            if response.status_code == 200:
                data = response.json()
                if data.get('code') == 0:
                    result_data = data.get('data', {})
                    question_count = result_data.get('questionCount', 0)
                    failed_count = result_data.get('faildCount', 0)

                    logger.info(f"✅ [API响应] 成功 - 总题数: {question_count}, 失败: {failed_count}")

                    return result_data
                else:
                    logger.error(f"❌ 提交答案失败: {data.get('msg', '未知错误')}")
                    return None
            else:
                logger.error(f"❌ 提交答案失败，状态码: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"❌ 提交答案异常: {str(e)}")
            return None

    def match_answer_from_bank(self, api_question: Dict, question_bank: Dict, knowledge: Optional[Dict] = None, verbose: bool = False) -> Optional[List[str]]:
        """
        从题库中匹配答案（API模式）

        Args:
            api_question: API返回的题目信息
                {
                    "questionID": "题目ID",
                    "questionTitle": "题目内容",
                    "questionsType": 0,  # 0=单选, 1=多选
                    "answerList": [...]
                }
            question_bank: 题库数据
            knowledge: 当前知识点对象（用于限定搜索范围）
            verbose: 是否打印详细日志（默认False）

        Returns:
            Optional[List[str]]: 正确答案的answerID列表，如果未找到则返回None
        """
        if not question_bank:
            if verbose:
                logger.warning("⚠️ 题库未加载")
            return None

        try:
            question_id = api_question.get('questionID')
            question_title = api_question.get('questionTitle', '')

            # 标准化题目标题
            title_normalized = self._normalize_text(question_title)

            if verbose:
                logger.info(f"🔍 匹配题目: {title_normalized[:60]}...")
                logger.info(f"   题目ID: {question_id}")

            # 获取题库章节列表
            chapters = get_chapters(question_bank)

            # 方式1：通过questionID精确匹配（委托共享匹配器 src.utils.bank_matcher）
            if question_id:
                correct_ids = find_correct_answer_ids(
                    question_bank, question_id, scope_knowledge=knowledge
                )
                if correct_ids:
                    if verbose:
                        logger.info(f"✅ ID匹配成功（{len(correct_ids)} 个正确选项）")
                    return correct_ids

                if verbose:
                    if knowledge:
                        logger.warning(f"⚠️ 在当前知识点未找到匹配的题目ID")
                    else:
                        logger.warning("⚠️ 未找到匹配的题目ID，尝试标题匹配")

            # 方式2：通过标题匹配（备用）
            candidates = []

            # 如果提供了knowledge，只在该知识点内搜索
            search_knowledges = []
            if knowledge:
                search_knowledges = [(knowledge, knowledge.get("Knowledge", "当前知识点"))]
            else:
                # 否则全局搜索
                for chapter in chapters:
                    for kn in chapter.get("knowledges", []):
                        search_knowledges.append((kn, kn.get("Knowledge", "")))

            for kn, kn_name in search_knowledges:
                for bank_question in kn.get("questions", []):
                    bank_title = bank_question.get("QuestionTitle", "")
                    bank_title_normalized = self._normalize_text(bank_title)

                    # 计算标题相似度
                    if title_normalized == bank_title_normalized:
                        # 完全匹配
                        candidates.append({
                            'question': bank_question,
                            'score': 100,
                            'knowledge': kn_name
                        })
                        break
                    elif title_normalized in bank_title_normalized or bank_title_normalized in title_normalized:
                        # 部分匹配
                        candidates.append({
                            'question': bank_question,
                            'score': 80,
                            'knowledge': kn_name
                        })

            if candidates:
                # 选择评分最高的候选
                best_match = max(candidates, key=lambda x: x['score'])

                if best_match['score'] >= 80:
                    if verbose:
                        logger.info(f"✅ 标题匹配成功（评分: {best_match['score']}%，知识点: {best_match['knowledge']}）")

                    # 直接使用题库中的选项ID
                    bank_options = best_match['question'].get("options", [])
                    correct_ids = []

                    for opt in bank_options:
                        if opt.get("isTrue"):
                            option_id = opt.get("id")
                            if option_id:
                                correct_ids.append(option_id)
                                if verbose:
                                    logger.info(f"   ✅ 正确答案: ID={option_id[:8]}...")

                    if correct_ids:
                        if verbose:
                            logger.info(f"   ⚡ 直接使用题库选项ID: {len(correct_ids)} 个")
                        return correct_ids

            if verbose:
                logger.warning(f"❌ 未在题库中找到匹配的答案")
            return None

        except Exception as e:
            if verbose:
                logger.error(f"❌ 匹配答案失败: {str(e)}")
                import traceback
                traceback.print_exc()
            return None

    def _find_knowledge_in_bank(self, kp_id: str, kp_name: str, question_bank: Dict) -> Optional[Dict]:
        """
        在题库中查找匹配的知识点

        Args:
            kp_id: API返回的知识点ID
            kp_name: API返回的知识点名称
            question_bank: 题库数据

        Returns:
            Optional[Dict]: 匹配的知识点对象，如果未找到则返回None
        """
        # 获取题库章节列表
        chapters = get_chapters(question_bank)

        # 遍历查找匹配的知识点
        for chapter in chapters:
            for bank_knowledge in chapter.get("knowledges", []):
                # 方式1：通过KnowledgeID匹配
                if bank_knowledge.get("KnowledgeID") == kp_id:
                    return bank_knowledge

                # 方式2：通过名称匹配
                bank_kp_name = bank_knowledge.get("Knowledge", "")
                if kp_name and bank_kp_name == kp_name:
                    return bank_knowledge

        return None

    def auto_answer_course(self, ecourse_id: str, question_bank: Dict, skip_completed: bool = True) -> Dict:
        """
        自动完成整个课程（API模式）

        Args:
            ecourse_id: 课程ID
            question_bank: 题库数据
            skip_completed: 是否跳过已完成的知识点（默认True）

        Returns:
            Dict: 做题统计结果
            {
                'total_knowledge': 0,      // 总知识点数
                'completed_knowledge': 0,   // 已完成知识点数
                'processed_knowledge': 0,   // 处理的知识点数
                'success_knowledge': 0,     // 成功的知识点数
                'failed_knowledge': 0,      // 失败的知识点数
                'skipped_knowledge': 0,     // 跳过的知识点数
                'total_questions': 0,       // 总题目数
                'matched_questions': 0,     // 匹配到的题目数
                'unmatched_questions': 0    // 未匹配的题目数
            }
        """
        result = {
            'total_knowledge': 0,
            'completed_knowledge': 0,
            'processed_knowledge': 0,
            'success_knowledge': 0,
            'failed_knowledge': 0,
            'skipped_knowledge': 0,
            'total_questions': 0,
            'matched_questions': 0,
            'unmatched_questions': 0
        }

        try:
            logger.info("\n" + "=" * 60)
            logger.info("🚀 开始API模式自动做题")
            logger.info("=" * 60)

            # 1. 获取课程树
            course_tree = self.get_course_tree(ecourse_id)

            if not course_tree:
                logger.error("❌ 获取课程树失败")
                return result

            course_name = course_tree.get('coursenName', '未知课程')
            chapter_list = course_tree.get('chapterList', [])

            logger.info(f"✅ 课程名称: {course_name}")
            logger.info(f"   章节数: {len(chapter_list)}")

            # 2. 遍历每个章节和知识点
            for chapter_idx, chapter in enumerate(chapter_list):
                chapter_title = chapter.get('titleContent', f'第{chapter_idx+1}章')
                knowledge_list = chapter.get('teacherKPList', [])

                result['total_knowledge'] += len(knowledge_list)

                for kp_idx, knowledge in enumerate(knowledge_list):
                    kp_id = knowledge.get('kpid')
                    kp_name = knowledge.get('knowledge', f'知识点{kp_idx+1}')
                    is_pass = knowledge.get('isPass')

                    logger.info(f"\n正在做 {chapter_title} - {kp_name}")

                    # 检查是否需要做这个知识点
                    if is_pass is True:
                        result['completed_knowledge'] += 1
                        if skip_completed:
                            logger.info(f"⏭️  已跳过（已完成）")
                            result['skipped_knowledge'] += 1
                            continue
                        else:
                            logger.info(f"🔄 重新作答")

                    result['processed_knowledge'] += 1

                    # 3. 获取题目列表
                    question_list = self.get_question_list(kp_id)

                    if not question_list:
                        logger.warning(f"⚠️  该知识点没有题目")
                        continue

                    logger.info(f"已获取题目列表 ({len(question_list)} 题)")
                    result['total_questions'] += len(question_list)

                    # 在题库中查找对应的知识点（用于限定搜索范围）
                    bank_knowledge = self._find_knowledge_in_bank(kp_id, kp_name, question_bank)
                    if bank_knowledge:
                        logger.info(f"已在题库中找到该知识点")
                    else:
                        logger.warning(f"⚠️  未在题库中找到对应的知识点，将全局搜索")

                    # 4. 匹配答案并构建提交数据
                    submit_data = []
                    failed_questions = []  # 记录失败的题目详情

                    for q_idx, question in enumerate(question_list):
                        question_id = question.get('questionID')
                        question_title = question.get('questionTitle', '')
                        question_type = question.get('questionsType', 0)  # 0=单选, 1=多选

                        # 从题库匹配答案（传入知识点限定搜索范围）
                        answer_ids = self.match_answer_from_bank(question, question_bank, bank_knowledge, verbose=False)

                        if answer_ids:
                            result['matched_questions'] += 1

                            # 多选题：多个answerID用逗号分隔
                            if question_type == 1:
                                answer_id_str = ','.join(answer_ids)
                            else:
                                answer_id_str = answer_ids[0] if answer_ids else ''

                            # 构建提交数据
                            submit_data.append({
                                'kpid': kp_id,
                                'questionID': question_id,
                                'answerID': answer_id_str
                            })
                        else:
                            result['unmatched_questions'] += 1
                            # 记录失败题目的详细信息
                            failed_questions.append({
                                'index': q_idx + 1,
                                'id': question_id,
                                'title': self._normalize_text(question_title)[:80]
                            })

                    # 打印匹配结果
                    matched = len(submit_data)
                    failed = len(failed_questions)
                    logger.info(f"已匹配完成 (成功: {matched}, 失败: {failed})")

                    # 如果有失败，打印详细日志
                    if failed_questions:
                        logger.warning("\n❌ 以下题目未匹配到答案：")
                        for fq in failed_questions:
                            logger.warning(f"   题{fq['index']}: {fq['title']}...")
                            logger.warning(f"      ID: {fq['id']}")

                    # 5. 提交答案
                    if submit_data:
                        logger.info("正在构建API请求...")
                        logger.info("发送请求...")
                        submit_result = self.submit_answers(submit_data)

                        if submit_result:
                            failed_count = submit_result.get('faildCount', 0)

                            if failed_count == 0:
                                logger.info(f"状态：✅ 知识点全部正确！")
                                result['success_knowledge'] += 1
                            else:
                                logger.warning(f"状态：⚠️  有 {failed_count} 题错误")
                                result['failed_knowledge'] += 1
                        else:
                            logger.error(f"状态：❌ 提交失败")
                            result['failed_knowledge'] += 1
                    else:
                        logger.warning(f"状态：⚠️  没有可提交的答案（{len(failed_questions)} 题未匹配）")
                        result['failed_knowledge'] += 1

            # 6. 输出统计结果
            logger.info("\n" + "=" * 60)
            logger.info("📊 做题统计")
            logger.info("=" * 60)
            logger.info(f"知识点: 成功 {result['success_knowledge']} | 失败 {result['failed_knowledge']} | 跳过 {result['skipped_knowledge']}")
            logger.info(f"题目: 总数 {result['total_questions']} | 匹配 {result['matched_questions']} | 未匹配 {result['unmatched_questions']}")
            logger.info("=" * 60)

            return result

        except Exception as e:
            logger.error(f"❌ 自动做题失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return result

"""
答案匹配 Mixin

从 AutoAnswer 中提取的题库/API 答案匹配逻辑。所有方法浏览器无关（不访问 page），
仅依赖题库数据与文本工具。作为 Mixin 混入 AutoAnswer，方法保持 self.* 形式，
调用方零改动。

宿主类需提供：
- self.question_bank            — 题库字典
- self.current_chapter          — 当前章节名（用于 _find_answer_in_bank 范围定位）
- self.current_knowledge        — 当前知识点名
- self.current_knowledge_index  — 当前知识点在章节中的索引
- self.current_api_question_ids — API 返回的题目 ID 列表（按顺序）
- self.current_api_question_titles — API 返回的题目标题列表
- self.current_question_index   — 当前题目索引（0-based）
- self.api_order_verified       — API 顺序是否已验证（可读写）
- self._normalize_text(text)    — 文本标准化（thin wrapper around normalize_text）
"""

import os
import re
import logging
from typing import Dict, List, Optional

from src.utils.text import get_chapters

logger = logging.getLogger(__name__)


class AnswerMatcherMixin:
    """答案匹配逻辑 Mixin：从题库/API 查找题目正确选项。浏览器无关。"""

    def _find_answer_from_api(self, question: Dict) -> Optional[List[str]]:
        """
        从API捕获的数据中查找当前题目的答案

        策略：
        1. 如果是第一题（索引0），验证题目标题是否与API第一题匹配
        2. 如果验证通过，信任整个顺序
        3. 使用当前题目索引从API题目ID列表中获取题目ID
        4. 在题库中通过题目ID查找对应题目
        5. 从题库中获取答案并匹配到当前页面的选项

        Args:
            question: 当前题目信息字典

        Returns:
            Optional[List[str]]: 正确选项的value列表，如果未找到则返回None
        """
        if not self.current_api_question_ids or not self.question_bank:
            return None

        try:
            # 使用当前题目索引
            current_index = self.current_question_index

            if current_index >= len(self.current_api_question_ids):
                logger.warning(f"⚠️ 当前题目索引 {current_index} 超出API返回的题目数量 {len(self.current_api_question_ids)}")
                return None

            # 如果是第一题，验证顺序是否正确
            if current_index == 0 and not self.api_order_verified:
                current_title = question.get('title', '')
                api_first_title = self.current_api_question_titles[0] if self.current_api_question_titles else ''

                logger.info(f"🔍 验证第一题顺序...")
                logger.info(f"   网页第一题: {current_title[:60]}...")
                logger.info(f"   API第一题: {api_first_title[:60]}...")

                # 简单验证：标题是否包含相同的关键词
                # 移除空格和标点后比较
                current_clean = re.sub(r'[^\w一-龥]', '', current_title)
                api_clean = re.sub(r'[^\w一-龥]', '', api_first_title)

                if current_clean == api_clean or (len(current_clean) > 10 and current_clean in api_clean) or (len(api_clean) > 10 and api_clean in current_clean):
                    self.api_order_verified = True
                    logger.info("✅ 第一题匹配成功，API顺序验证通过")
                else:
                    logger.warning("⚠️ 第一题不匹配，API顺序可能不正确，将使用题库匹配")
                    return None

            # 如果顺序已验证，或者直接信任（跳过验证）
            api_question_id = self.current_api_question_ids[current_index]
            logger.info(f"✅ 当前是第{current_index + 1}题，API题目ID: {api_question_id[:8]}...")

            return self._find_answer_in_bank_by_question_id(api_question_id, question)

        except Exception as e:
            logger.error(f"❌ 从API数据查找答案失败: {str(e)}")
            return None

    def _find_answer_in_bank_by_question_id(self, question_id: str, current_question: Dict) -> Optional[List[str]]:
        """
        在题库中通过题目ID查找答案
        使用选项顺序（oppentionOrder）直接匹配，不需要内容匹配

        Args:
            question_id: 题目ID（从API获取）
            current_question: 当前题目信息（用于选项匹配）

        Returns:
            Optional[List[str]]: 正确选项的value列表
        """
        try:
            logger.info(f"🔍 在题库中查找题目ID: {question_id[:8]}...")

            # 获取当前页面的选项列表
            current_options = current_question.get('options', [])

            # 遍历题库查找匹配的题目
            chapters = get_chapters(self.question_bank)

            for chapter in chapters:
                for knowledge in chapter.get("knowledges", []):
                    for bank_question in knowledge.get("questions", []):
                        # 检查题目ID是否匹配
                        if bank_question.get("QuestionID") == question_id:
                            logger.info(f"✅ 在题库中找到题目: {bank_question.get('QuestionTitle', '')[:50]}...")

                            # 获取正确答案的选项顺序
                            bank_options = bank_question.get("options", [])
                            correct_orders = []

                            for opt in bank_options:
                                if opt.get("isTrue"):
                                    order = opt.get("oppentionOrder", 0)
                                    correct_orders.append(order)

                            if not correct_orders:
                                logger.warning("⚠️ 题库中未标记正确答案")
                                return None

                            logger.info(f"   正确选项顺序(oppentionOrder): {correct_orders}")

                            # 根据顺序直接获取页面对应位置的选项
                            # oppentionOrder 有两种格式：
                            # - 格式1: 0, 10, 20, 30（需要除以10）
                            # - 格式2: 0, 1, 2, 3（直接使用）
                            correct_values = []
                            for order in correct_orders:
                                # 判断格式并转换为索引
                                if order >= 10:
                                    option_index = order // 10  # 0→0, 10→1, 20→2, 30→3
                                    format_type = "格式1(除以10)"
                                else:
                                    option_index = order  # 0→0, 1→1, 2→2, 3→3
                                    format_type = "格式2(直接使用)"

                                if option_index < len(current_options):
                                    option_value = current_options[option_index]['value']
                                    option_label = current_options[option_index]['label']
                                    correct_values.append(option_value)
                                    logger.info(f"   选项顺序 {order} ({format_type}) → 索引 {option_index} → {option_label}选项 (value: {option_value[:8] if option_value else 'N/A'}...)")
                                else:
                                    logger.warning(f"⚠️ 选项索引 {option_index} 超出范围（共 {len(current_options)} 个选项）")

                            if correct_values:
                                logger.info(f"   正确选项value: {correct_values}")
                                return correct_values
                            else:
                                logger.warning("⚠️ 无法匹配到当前页面的选项value")
                                return None

            logger.warning(f"⚠️ 题库中未找到题目ID: {question_id[:8]}...")
            return None

        except Exception as e:
            logger.error(f"❌ 查找题库失败: {str(e)}")
            return None

    def _find_answer_in_bank(self, question: Dict) -> Optional[List[str]]:
        """
        在题库中查找匹配的答案（仅在当前知识点范围内搜索）

        Args:
            question: 题目信息字典

        Returns:
            Optional[List[str]]: 正确选项的value列表，如果未找到则返回None
        """
        if not self.question_bank:
            logger.warning("⚠️ 题库未加载")
            return None

        try:
            question_title = question['title']
            question_type = question['type']
            question_options = question.get('options', [])

            # 存储所有候选题目及其得分
            candidates = []

            # 检查是否有当前位置信息
            if not self.current_chapter or self.current_knowledge_index is None:
                logger.error("❌ 未记录当前章节和知识点信息，无法搜索题库")
                logger.info("   提示：请确保先调用 find_and_click_avaliable_knowledge() 方法")
                return None

            logger.info(f"🎯 在当前知识点范围内搜索: {self.current_chapter} > 索引{self.current_knowledge_index}")

            # 遍历题库查找匹配的题目
            chapters = get_chapters(self.question_bank)

            # 在当前章节中查找（按名称匹配）
            target_chapter = None
            for chapter in chapters:
                chapter_title = chapter.get("chapterTitle", "")
                if self._text_contains(chapter_title, self.current_chapter):
                    target_chapter = chapter
                    break

            if not target_chapter:
                logger.error(f"❌ 在题库中未找到章节: {self.current_chapter}")
                logger.info(f"   可用章节: {[ch.get('chapterTitle', '') for ch in chapters[:5]]}...")
                return None

            logger.debug(f"✅ 找到章节: {target_chapter.get('chapterTitle', '')}")

            # 在当前知识点中查找（按索引匹配）
            knowledges = target_chapter.get("knowledges", [])
            if self.current_knowledge_index >= len(knowledges):
                logger.error(f"❌ 知识点索引 {self.current_knowledge_index} 超出范围，该章节共有 {len(knowledges)} 个知识点")
                logger.info(f"   可用知识点: {[k.get('Knowledge', '') for k in knowledges[:5]]}...")
                return None

            target_knowledge = knowledges[self.current_knowledge_index]
            logger.info(f"✅ 按索引找到知识点: {target_knowledge.get('Knowledge', '')} (第{self.current_knowledge_index+1}个)")
            logger.info(f"📋 该知识点共有 {len(target_knowledge.get('questions', []))} 道题目")

            # 遍历当前知识点的所有题目
            questions = target_knowledge.get("questions", [])

            # 调试：显示前3道题库题目的标题
            logger.debug(f"📚 题库前3道题目:")
            for i, q in enumerate(questions[:3]):
                q_title = self._normalize_text(q.get("QuestionTitle", ""))
                logger.debug(f"   {i+1}. {q_title[:50]}...")

            logger.debug(f"🔍 当前题目: {question_title[:50]}...")

            for bank_question in questions:
                # 获取题库中的题目标题（原始HTML）
                bank_title_raw = bank_question.get("QuestionTitle", "")

                # 检查题库题目是否包含图片，提取图片名称
                bank_image_name = None
                bank_img_match = re.search(r'<img[^>]+src=["\']?/oss/api/ImageViewer/([^"\']+?)["\']?', bank_title_raw)
                if bank_img_match:
                    # 提取图片文件名（不含扩展名和参数）
                    bank_image_path = bank_img_match.group(1)
                    bank_image_name = os.path.splitext(bank_image_path.split('?')[0])[0]

                # 标准化题库中的题目标题
                bank_title = self._normalize_text(bank_title_raw)

                # 如果题库题目包含图片，添加图片标识
                if bank_image_name:
                    bank_title = f"[图片:{bank_image_name}] {bank_title}"

                bank_options = bank_question.get("options", [])

                # 计算标题匹配度
                title_match = self._match_question(question_title, bank_title)
                title_score = 0
                if title_match:
                    # 计算标题相似度（字符串长度比）
                    title_score = min(len(question_title), len(bank_title)) / max(len(question_title), len(bank_title))

                # 计算选项匹配度
                # _match_by_options 仅在「全部选项匹配」时返回 True，故 option_score ∈ {0, 1.0}
                # （等价于原内联重算 matched_count/total 的结果，但消除了重复的匹配循环）
                option_score = 1.0 if (question_options and bank_options and self._match_by_options(question_options, bank_options)) else 0

                # 综合得分：标题权重60%，选项权重40%
                total_score = title_score * 0.6 + option_score * 0.4

                # 如果标题或选项有匹配，记录为候选
                if title_match or (option_score > 0.5):
                    candidates.append({
                        'question': bank_question,
                        'bank_title': bank_title,
                        'bank_options': bank_options,
                        'title_score': title_score,
                        'option_score': option_score,
                        'total_score': total_score
                    })

            # 如果没有找到任何候选，返回失败
            if not candidates:
                logger.warning(f"⚠️ 在当前知识点中未找到匹配的题目")
                logger.info(f"   当前题目: {question_title[:100]}...")
                logger.info(f"   当前位置: {self.current_chapter} > {self.current_knowledge}")
                logger.info(f"   💡 提示：该知识点共有 {len(questions)} 道题，但无法匹配当前题目")
                return None

            # 按综合得分排序，选择最匹配的题目
            candidates.sort(key=lambda x: x['total_score'], reverse=True)

            best_match = candidates[0]
            logger.info(f"✅ 在题库中找到最佳匹配题目（综合得分:{best_match['total_score']:.2f}）")
            logger.info(f"   📊 标题相似度: {best_match['title_score']:.2f}, 选项相似度: {best_match['option_score']:.2f}")
            logger.info(f"   📍 当前位置: {self.current_chapter} > {self.current_knowledge}")
            logger.info(f"   题目: {question_title[:50]}...")

            # 如果最高得分太低（<0.5），可能匹配不准确
            if best_match['total_score'] < 0.5:
                logger.warning(f"⚠️ 匹配度较低，可能不准确")
                logger.info(f"   题库题目: {best_match['bank_title'][:80]}...")

            # 获取正确答案的内容文本
            correct_contents = []
            for option in best_match['bank_options']:
                if option.get("isTrue", False):
                    content = option.get("oppentionContent", "")
                    content_normalized = self._normalize_text(content)
                    if content_normalized:
                        correct_contents.append(content_normalized)

            if not correct_contents:
                logger.warning(f"⚠️ 题库中该题目没有标记正确答案")
                return None

            # 在当前页面选项中通过内容匹配找到对应的value
            current_options = question.get('options', [])
            matched_values = []

            for correct_content in correct_contents:
                for page_option in current_options:
                    page_content = page_option.get('content', '')
                    page_content_normalized = self._normalize_text(page_content)

                    # 使用宽松匹配
                    if self._text_contains(page_content_normalized, correct_content):
                        matched_values.append(page_option.get('value', ''))
                        logger.info(f"   匹配成功: {correct_content[:30]}... → value: {page_option.get('value', '')[:8]}...")
                        break

            if matched_values:
                logger.info(f"   正确答案: {len(matched_values)} 个选项")
                return matched_values
            else:
                logger.warning(f"⚠️ 未能将题库答案匹配到页面选项")
                return None

        except Exception as e:
            logger.error(f"❌ 在题库中查找答案失败: {str(e)}")
            return None

    def _text_contains(self, text: str, keyword: str) -> bool:
        """
        检查文本是否包含关键词（宽松匹配）

        Args:
            text: 文本（通常来自题库，如"项目3"）
            keyword: 关键词（通常来自网页，如"项目3 统计成绩单--循环结构"）

        Returns:
            bool: 是否包含
        """
        if not text or not keyword:
            return False

        # 标准化两个文本
        text_normalized = self._normalize_text(text)
        keyword_normalized = self._normalize_text(keyword)

        # 包含匹配（双向包含，处理长包含短和短包含长的情况）
        if keyword_normalized in text_normalized or text_normalized in keyword_normalized:
            logger.info(f"   ✅ 包含匹配成功: '{text_normalized}' ⊆ '{keyword_normalized[:30]}...'")
            return True

        # 如果关键词很短（少于10个字符），尝试部分匹配
        # 例如："项目3" 应该能匹配 "项目3 统计成绩单"
        if len(keyword_normalized) < 10 and len(text_normalized) > len(keyword_normalized):
            # 检查关键词是否是文本的前缀
            if text_normalized.startswith(keyword_normalized):
                logger.info(f"   ✅ 前缀匹配: '{keyword_normalized}' ⊆ '{text_normalized[:30]}...'")
                return True

            # 检查是否包含关键词中的主要部分（去除空格和标点）
            keyword_core = re.sub(r'[^\w一-龥]', '', keyword_normalized)
            text_core = re.sub(r'[^\w一-龥]', '', text_normalized)
            if keyword_core and keyword_core in text_core:
                logger.info(f"   ✅ 核心词匹配: '{keyword_core}' ⊆ '{text_core[:30]}...'")
                return True

        logger.warning(f"   ⚠️ 匹配失败:")
        logger.warning(f"      题库文本: '{text_normalized}'")
        logger.warning(f"      网页关键词: '{keyword_normalized}'")
        return False

    def _match_question(self, question1: str, question2: str) -> bool:
        """
        匹配两个题目是否相同

        Args:
            question1: 题目1
            question2: 题目2

        Returns:
            bool: 是否匹配
        """
        # 完全匹配
        if question1 == question2:
            logger.debug(f"   ✅ 完全匹配: '{question1[:50]}...'")
            return True

        # 包含匹配（需要确保包含的不仅是通用关键词）
        if question1 in question2 or question2 in question1:
            # 检查是否包含足够长的独特内容（至少30个字符）
            shorter = question1 if len(question1) < len(question2) else question2
            if len(shorter) >= 30:
                # 进一步检查：确保包含代码中的独特部分
                # 提取可能的代码行（包含=;[]()等符号的部分）
                code_parts1 = re.findall(r'[a-zA-Z_]\w*\s*[=+\-*/]\s*[^;]+;?', question1)
                code_parts2 = re.findall(r'[a-zA-Z_]\w*\s*[=+\-*/]\s*[^;]+;?', question2)

                # 如果两道题都有代码部分，检查是否有相同的代码行
                if code_parts1 and code_parts2:
                    for code1 in code_parts1:
                        for code2 in code_parts2:
                            if code1.strip() == code2.strip() and len(code1.strip()) > 10:
                                logger.debug(f"   ✅ 包含匹配（含相同代码）: '{code1[:30]}...'")
                                return True

                # 如果没有代码部分或代码部分不匹配，但整体包含，也认为匹配
                logger.debug(f"   ✅ 包含匹配: '{question1[:30]}...' ⊆ '{question2[:30]}...'")
                return True

        # 移除标点和空格后匹配
        q1_clean = re.sub(r'[^\w一-龥]', '', question1)
        q2_clean = re.sub(r'[^\w一-龥]', '', question2)

        if q1_clean == q2_clean:
            logger.debug(f"   ✅ 清理后匹配: '{q1_clean[:30]}...'")
            return True

        logger.debug(f"   ❌ 匹配失败:")
        logger.debug(f"      题目1: {question1[:80]}")
        logger.debug(f"      题目2: {question2[:80]}")
        return False

    def _match_by_options(self, current_options: List[Dict], bank_options: List[Dict]) -> bool:
        """
        通过选项内容进行匹配（用于带图片的题目）

        Args:
            current_options: 当前题目的选项列表
            bank_options: 题库中题目的选项列表

        Returns:
            bool: 选项是否匹配
        """
        try:
            # 提取当前题目的选项内容
            current_contents = []
            for opt in current_options:
                content = self._normalize_text(opt.get('content', ''))
                if content:
                    current_contents.append(content)

            # 提取题库中的选项内容
            bank_contents = []
            for opt in bank_options:
                content = self._normalize_text(opt.get('oppentionContent', ''))
                if content:
                    bank_contents.append(content)

            # 如果选项数量不匹配，直接返回False
            if len(current_contents) != len(bank_contents):
                return False

            # 检查所有选项是否都匹配
            matched_count = 0
            for curr_content in current_contents:
                for bank_content in bank_contents:
                    if curr_content == bank_content or curr_content in bank_content or bank_content in curr_content:
                        matched_count += 1
                        break

            # 如果所有选项都匹配，返回True
            return matched_count == len(current_contents)

        except Exception as e:
            logger.debug(f"选项匹配失败: {str(e)}")
            return False

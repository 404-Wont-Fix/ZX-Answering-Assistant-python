"""
自动做题模块
用于在学生端自动作答题目
"""

from typing import Dict, List, Optional, Tuple
import html
import os
import re
import time
import logging
import threading

from src.utils.text import normalize_text
from src.utils.logging import setup_callback_logging, cleanup_callback_logging
from src.answering.base_answer import BaseAnswer
from src.answering._answer_matcher import AnswerMatcherMixin

logger = logging.getLogger(__name__)


class AutoAnswer(BaseAnswer, AnswerMatcherMixin):
    """自动做题类"""

    def __init__(self, page=None, log_callback=None):
        """
        初始化自动做题器

        Args:
            page: Playwright页面对象（已弃用，保留用于向后兼容）
            log_callback: 日志回调函数（可选），用于将日志输出到GUI
        """
        self.page = None  # 不再存储 page 对象，改为动态获取
        self.question_bank = None  # 题库数据
        self.current_chapter = None  # 当前章节信息
        self.current_knowledge = None  # 当前知识点信息
        self.current_knowledge_index = None  # 当前知识点在章节中的索引（用于按顺序匹配）
        self.current_api_question_ids = []  # 当前API返回的题目ID列表（按顺序）
        self.current_api_question_titles = []  # 当前API返回的题目标题列表（按顺序，用于验证）
        self.api_order_verified = False  # API题目顺序是否已验证
        self.current_question_index = 0  # 当前题目的索引（0-based）
        self.api_listener_active = False  # API监听器是否激活

        # 优雅退出控制相关
        self._is_answering_question = False  # 是否正在答题
        self._is_processing_knowledge = False  # 是否正在处理知识点
        self._stop_requested = False  # 是否请求停止

        # 日志回调
        self._log_callback = log_callback

        # 设置日志处理器
        self._setup_log_handler()

    def _get_page(self):
        """
        动态获取当前的页面对象
        每次调用都从 browser_manager 获取，确保在线程安全的环境中

        Returns:
            Page: Playwright页面对象，如果获取失败返回None
        """
        try:
            from src.core.browser import get_browser_manager, BrowserType
            manager = get_browser_manager()
            _, page = manager.get_context_and_page(BrowserType.STUDENT)
            return page
        except Exception as e:
            logger.error(f"获取页面对象失败: {e}")
            return None

    def _setup_log_handler(self):
        """设置日志处理器，将日志转发到回调函数"""
        self._log_handler = setup_callback_logging(logger, self._log_callback)

    def _cleanup_log_handler(self):
        """清理日志处理器"""
        cleanup_callback_logging(logger, self._log_handler)
        self._log_handler = None

    def _check_page_alive(self) -> bool:
        """
        检查 page 对象是否仍然可用

        Returns:
            bool: page 是否可用
        """
        try:
            # 动态获取 page 对象并检查连接状态
            page = self._get_page()
            if not page:
                return False
            # 尝试访问 page 的 URL 属性来检查连接状态
            _ = page.url
            return True
        except Exception as e:
            logger.warning(f"⚠️ 页面连接检查失败: {str(e)}")
            return False

    def load_question_bank(self, question_bank_data: Dict):
        """
        加载题库数据

        Args:
            question_bank_data: 题库数据（从JSON文件导入）
        """
        self.question_bank = question_bank_data
        logger.info("✅ 题库数据已加载")

    def request_stop(self):
        """请求停止（GUI调用）"""
        self._stop_requested = True
        print("\n\n🛑 用户请求停止...")
        logger.info("🛑 用户请求停止...")

        if self._is_answering_question:
            print("⏳ 当前正在答题，完成后将停止...")
            logger.info("⏳ 当前正在答题，完成后将停止...")
        elif self._is_processing_knowledge:
            print("⏳ 当前正在处理知识点，完成后将停止...")
            logger.info("⏳ 当前正在处理知识点，完成后将停止...")
        else:
            print("🛑 立即停止...")
            logger.info("🛑 立即停止...")

    def _check_stop(self) -> bool:
        """检查是否应该停止"""
        if self._stop_requested:
            self._stop_requested = False
            return True
        return False

    def start_api_listener(self):
        """启动全局API监听器（捕获beginevaluate API）"""
        if self.api_listener_active:
            logger.debug("API监听器已经在运行")
            return

        def handle_response(response):
            # 只监听beginevaluate API
            if "beginevaluate" in response.url:
                try:
                    data = response.json()
                    if data.get("code") == 0 and "data" in data:
                        api_data = data["data"]
                        question_list = api_data.get("questionList", [])

                        # 保存题目ID和标题
                        self.current_api_question_ids = [q.get('id') for q in question_list]
                        self.current_api_question_titles = []
                        for q in question_list:
                            title_html = q.get('questionTitle', '')
                            title_text = self._normalize_text(title_html)
                            self.current_api_question_titles.append(title_text)

                        logger.info(f"✅ 捕获到beginevaluate API")
                        logger.info(f"   题目ID列表: {len(self.current_api_question_ids)} 个")
                        logger.info(f"   第1题标题: {self.current_api_question_titles[0][:50] if self.current_api_question_titles else ''}...")
                except Exception as e:
                    logger.debug(f"解析API响应失败: {str(e)}")

        self._get_page().on("response", handle_response)
        self.api_listener_active = True
        logger.info("✅ 全局API监听器已启动")

    def stop_api_listener(self):
        """停止全局API监听器"""
        if not self.api_listener_active:
            return

        # Playwright不支持移除特定监听器，只能通过标志控制
        self.api_listener_active = False
        logger.info("✅ 全局API监听器已停止")

    def _normalize_text(self, text: str) -> str:
        """标准化文本，用于匹配"""
        return normalize_text(text, preserve_angles=True)
    def _parse_question_type(self) -> Tuple[str, str]:
        """
        解析题目类型

        Returns:
            Tuple[str, str]: (题目类型代码, 题目类型名称)
                - 题目类型代码: 'single' (单选), 'multiple' (多选), 'judge' (判断)
                - 题目类型名称: '单选', '多选', '判断'
        """
        try:
            # 获取题目类型元素
            type_element = self._get_page().query_selector(".question-type")
            if not type_element:
                logger.warning("⚠️ 未找到题目类型元素，默认为单选题")
                return "single", "单选"

            type_text = type_element.text_content()

            if "多选" in type_text:
                return "multiple", "多选"
            elif "判断" in type_text:
                return "judge", "判断"
            else:
                return "single", "单选"

        except Exception as e:
            logger.error(f"❌ 解析题目类型失败: {str(e)}")
            return "single", "单选"

    def _parse_current_question(self) -> Optional[Dict]:
        """
        解析当前题目的信息

        Returns:
            Optional[Dict]: 题目信息字典，包含:
                {
                    'type': str,  # 题目类型: 'single', 'multiple', 'judge'
                    'title': str,  # 题目内容
                    'options': List[Dict],  # 选项列表
                        [
                            {
                                'label': str,  # 选项标签 (A, B, C, D)
                                'content': str,  # 选项内容
                                'value': str  # 选项value值
                            }
                        ]
                }
        """
        try:
            # 解析题目类型
            question_type, type_name = self._parse_question_type()

            # 获取题目标题
            title_element = self._get_page().query_selector(".question-title")
            if not title_element:
                logger.error("❌ 未找到题目标题元素")
                return None

            # 获取题目标题的HTML内容（用于检查是否包含图片）
            title_html = title_element.inner_html()

            # 检查是否包含图片
            image_name = None
            img_match = re.search(r'<img[^>]+src=["\']?/oss/api/ImageViewer/([^"\']+?)["\']?', title_html)
            if img_match:
                # 提取图片文件名（不含扩展名和参数）
                image_path = img_match.group(1)
                image_name = os.path.splitext(image_path.split('?')[0])[0]
                logger.info(f"📷 检测到图片题目: {image_name}")

            title_text = title_element.text_content()
            title_normalized = self._normalize_text(title_text)

            # 如果包含图片，将图片名称添加到题目标题中用于匹配
            if image_name:
                title_normalized = f"[图片:{image_name}] {title_normalized}"
                logger.debug(f"   题目标题（含图片标识）: {title_normalized[:100]}...")

            # 获取选项
            options = []

            if question_type in ["single", "judge"]:
                # 单选或判断题 - 使用 el-radio
                radio_labels = self._get_page().query_selector_all(".el-radio")
                for label in radio_labels:
                    # 获取选项标签（A、B、C、D）
                    label_element = label.query_selector(".option-answer")
                    label_text = label_element.text_content() if label_element else ""

                    # 获取选项内容
                    content_element = label.query_selector(".option-content")
                    content_text = content_element.text_content() if content_element else ""

                    # 获取value值
                    input_element = label.query_selector("input[type='radio']")
                    value = input_element.get_attribute("value") if input_element else ""

                    options.append({
                        'label': self._normalize_text(label_text),
                        'content': self._normalize_text(content_text),
                        'value': value
                    })

            elif question_type == "multiple":
                # 多选题 - 使用 el-checkbox
                checkbox_labels = self._get_page().query_selector_all(".el-checkbox")
                for label in checkbox_labels:
                    # 获取选项标签（A、B、C、D）
                    label_element = label.query_selector(".option-answer")
                    label_text = label_element.text_content() if label_element else ""

                    # 获取选项内容
                    content_element = label.query_selector(".option-content")
                    content_text = content_element.text_content() if content_element else ""

                    # 获取value值
                    input_element = label.query_selector("input[type='checkbox']")
                    value = input_element.get_attribute("value") if input_element else ""

                    options.append({
                        'label': self._normalize_text(label_text),
                        'content': self._normalize_text(content_text),
                        'value': value
                    })

            return {
                'type': question_type,
                'type_name': type_name,
                'title': title_normalized,
                'options': options
            }

        except Exception as e:
            logger.error(f"❌ 解析当前题目失败: {str(e)}")
            return None

    def find_and_click_avaliable_knowledge(self) -> bool:
        """
        查找并点击可作答的知识点
        会自动展开所有折叠的章节进行查找

        Returns:
            bool: 是否成功找到并点击
        """
        try:
            logger.info("🔍 查找可作答的知识点...")

            # 刷新网页以确保页面状态最新
            logger.info("🔄 刷新网页以确保知识点列表最新...")
            self._get_page().reload(wait_until="domcontentloaded")
            time.sleep(2)  # 等待页面完全加载
            logger.info("✅ 网页刷新完成")

            # 等待知识点列表加载
            self._get_page().wait_for_selector(".el-submenu", timeout=5000)

            # 获取所有章节（折叠菜单）
            chapters = self._get_page().query_selector_all(".el-submenu")

            logger.info(f"📋 找到 {len(chapters)} 个章节")

            knowledge_count = 0  # 统计检查的知识点总数

            # 遍历每个章节
            for chapter_idx, chapter in enumerate(chapters):
                try:
                    # 获取章节标题
                    chapter_title_elem = chapter.query_selector(".el-submenu__title span")
                    chapter_title = chapter_title_elem.text_content() if chapter_title_elem else f"第{chapter_idx+1}章"
                    logger.info(f"📖 检查章节: {chapter_title}")

                    # 点击章节标题展开（如果是折叠状态）
                    chapter_title_div = chapter.query_selector(".el-submenu__title")
                    if chapter_title_div:
                        # 检查章节是否已经展开
                        chapter_class = chapter.get_attribute("class") or ""
                        is_opened = "is-opened" in chapter_class

                        if not is_opened:
                            # 章节是折叠的，需要点击展开
                            chapter_title_div.click()
                            time.sleep(0.5)  # 等待展开动画
                            logger.debug(f"   ↕️  已展开章节")
                        else:
                            # 章节已经展开，不需要点击
                            logger.debug(f"   ✅ 章节已展开")

                    # 获取该章节下的所有知识点
                    knowledge_items = chapter.query_selector_all(".el-menu-item")
                    logger.info(f"   📝 该章节有 {len(knowledge_items)} 个知识点")

                    # 检查每个知识点
                    for knowledge_idx, item in enumerate(knowledge_items):
                        knowledge_count += 1

                        try:
                            # 获取知识点名称
                            knowledge_name_elem = item.query_selector("span.default, span:not([class])")
                            knowledge_name = knowledge_name_elem.text_content().strip() if knowledge_name_elem else f"知识点{knowledge_count}"

                            # 点击知识点切换到该知识点
                            item.click()
                            time.sleep(0.5)  # 等待内容加载

                            # 检查是否有"开始测评"或"第X次测评"按钮
                            start_button = None

                            # 方法1: 查找"开始测评"
                            try:
                                start_button = self._get_page().query_selector("button:has-text('开始测评')", timeout=1000)
                                if start_button:
                                    logger.info(f"✅ 找到可作答知识点: {knowledge_name}")
                                    # 记录当前章节和知识点信息
                                    self.current_chapter = chapter_title
                                    self.current_knowledge = knowledge_name
                                    self.current_knowledge_index = knowledge_idx  # 记录知识点索引
                                    logger.info(f"📍 当前位置: {chapter_title} > {knowledge_name} (索引:{knowledge_idx})")
                                    return True
                            except Exception:
                                pass

                            # 方法2: 查找"第X次测评"
                            if not start_button:
                                try:
                                    buttons = self._get_page().query_selector_all("button.el-button--primary")
                                    for btn in buttons:
                                        text = btn.text_content() or ""
                                        if "测评" in text:
                                            start_button = btn
                                            logger.info(f"✅ 找到可作答知识点: {knowledge_name} (按钮: {text.strip()})")
                                            # 记录当前章节和知识点信息
                                            self.current_chapter = chapter_title
                                            self.current_knowledge = knowledge_name
                                            self.current_knowledge_index = knowledge_idx  # 记录知识点索引
                                            logger.info(f"📍 当前位置: {chapter_title} > {knowledge_name} (索引:{knowledge_idx})")
                                            return True
                                except Exception:
                                    pass

                            # 没有找到测评按钮，说明已完成或次数用尽
                            # 检查是否有"已完成"或"测评次数"等提示信息
                            try:
                                status_info = self._get_page().query_selector(".evaluation-status, .status-info, .completed-tag")
                                if status_info:
                                    status_text = status_info.text_content() or ""
                                    if "3次" in status_text or "已完成" in status_text:
                                        logger.info(f"⏭️  跳过知识点: {knowledge_name} (状态: {status_text.strip()})")
                                    else:
                                        logger.debug(f"   ⏭️  {knowledge_name} - 已完成或不可作答")
                                else:
                                    logger.debug(f"   ⏭️  {knowledge_name} - 已完成或不可作答")
                            except Exception:
                                logger.debug(f"   ⏭️  {knowledge_name} - 已完成或不可作答")

                        except Exception as e:
                            logger.debug(f"   ⚠️  知识点 {knowledge_count} 检查失败 - {str(e)}")
                            continue

                except Exception as e:
                    logger.debug(f"章节 {chapter_idx+1} 检查失败 - {str(e)}")
                    continue

            logger.warning(f"⚠️ 所有 {knowledge_count} 个知识点都已完成或未找到可作答的知识点")
            return False

        except Exception as e:
            logger.error(f"❌ 查找可作答知识点失败: {str(e)}")
            return False

    def click_start_button_only(self) -> bool:
        """
        只点击"开始测评"按钮（不检索知识点）
        用于网站自动跳转后直接点击当前页面的按钮

        Returns:
            bool: 是否成功点击
        """
        try:
            logger.info("🎯 点击当前页面的开始测评按钮（不进行检索）...")

            # 等待页面加载完成
            logger.info("⏳ 等待页面加载...")
            time.sleep(2)

            # 尝试查找"开始测评"按钮
            start_button = None

            # 方法1: 查找包含"开始测评"文本的按钮
            try:
                start_button = self._get_page().wait_for_selector("button:has-text('开始测评')", timeout=5000)
                logger.info("✅ 找到'开始测评'按钮")
            except Exception:
                logger.info("⚠️ 未找到'开始测评'按钮，尝试查找'第X次测评'按钮")

            # 方法2: 查找包含"测评"文本的按钮（可能是重做）
            if not start_button:
                try:
                    buttons = self._get_page().query_selector_all("button.el-button--primary")
                    for btn in buttons:
                        text = btn.text_content()
                        if "测评" in text:
                            start_button = btn
                            logger.info(f"✅ 找到测评按钮: {text.strip()}")
                            break
                except Exception:
                    pass

            if not start_button:
                logger.info("⚠️ 未找到开始测评按钮，当前知识点可能已完成")
                return False

            # 点击按钮
            start_button.click()
            logger.info("✅ 已点击开始测评按钮")
            time.sleep(1)  # 等待弹窗出现
            return True

        except Exception as e:
            logger.error(f"❌ 点击开始测评按钮失败: {str(e)}")
            return False

    def click_start_button(self) -> bool:
        """
        点击"开始测评"按钮（包含检索功能）

        Returns:
            bool: 是否成功点击
        """
        try:
            # 首先尝试查找可作答的知识点
            if not self.find_and_click_avaliable_knowledge():
                return False

            logger.info("🎯 点击开始测评按钮...")

            # 尝试查找"开始测评"按钮
            start_button = None

            # 方法1: 查找包含"开始测评"文本的按钮
            try:
                start_button = self._get_page().wait_for_selector("button:has-text('开始测评')", timeout=2000)
                logger.info("✅ 找到'开始测评'按钮")
            except Exception:
                logger.info("⚠️ 未找到'开始测评'按钮，尝试查找'第X次测评'按钮")

            # 方法2: 查找包含"测评"文本的按钮（可能是重做）
            if not start_button:
                try:
                    buttons = self._get_page().query_selector_all("button.el-button--primary")
                    for btn in buttons:
                        text = btn.text_content()
                        if "测评" in text:
                            start_button = btn
                            logger.info(f"✅ 找到测评按钮: {text.strip()}")
                            break
                except Exception:
                    pass

            if not start_button:
                logger.error("❌ 未找到开始测评按钮")
                return False

            # 点击按钮
            start_button.click()
            logger.info("✅ 已点击开始测评按钮")
            time.sleep(1)  # 等待弹窗出现
            return True

        except Exception as e:
            logger.error(f"❌ 点击开始测评按钮失败: {str(e)}")
            return False

    def handle_confirm_dialog(self) -> bool:
        """
        处理确认弹窗（点击"确定"按钮）

        Returns:
            bool: 是否成功处理
        """
        try:
            logger.info("🔍 查找确认弹窗...")

            # 等待弹窗出现
            dialog_found = False
            try:
                dialog = self._get_page().wait_for_selector(".el-message-box", timeout=5000)
                if dialog:
                    dialog_found = True
                    logger.info("✅ 检测到确认弹窗")
            except Exception:
                logger.info("⚠️ 未检测到确认弹窗，可能已经进入答题界面")
                return True

            if not dialog_found:
                return True

            # 多种方法查找"确定"按钮
            confirm_button = None

            # 方法1: 在弹窗内查找主要按钮
            try:
                confirm_button = self._get_page().wait_for_selector(".el-message-box button.el-button--primary", timeout=2000)
                logger.info("✅ 方法1: 找到确定按钮")
            except Exception:
                logger.debug("⚠️ 方法1未找到")

            # 方法2: 查找包含"确定"文本的按钮
            if not confirm_button:
                try:
                    buttons = self._get_page().query_selector_all(".el-message-box button")
                    for btn in buttons:
                        text = btn.text_content() or ""
                        if "确定" in text:
                            confirm_button = btn
                            logger.info("✅ 方法2: 找到确定按钮")
                            break
                except Exception:
                    logger.debug("⚠️ 方法2未找到")

            # 方法3: 使用CSS选择器查找第二个按钮（确定按钮通常在第二个位置）
            if not confirm_button:
                try:
                    buttons = self._get_page().query_selector_all(".el-message-box__btns button")
                    if len(buttons) >= 2:
                        confirm_button = buttons[1]  # 第二个按钮通常是"确定"
                        logger.info("✅ 方法3: 找到确定按钮（第二个按钮）")
                except Exception:
                    logger.debug("⚠️ 方法3未找到")

            if not confirm_button:
                logger.error("❌ 未找到确定按钮")
                return False

            # 点击确定
            confirm_button.click()
            logger.info("✅ 已点击确定按钮")

            # 等待答题界面加载（API会由全局监听器捕获）
            time.sleep(3)

            # 检查是否捕获到API数据
            if self.current_api_question_ids:
                logger.info(f"✅ 全局监听器已捕获API数据 ({len(self.current_api_question_ids)} 道题)")
            else:
                logger.warning("⚠️ 全局监听器未捕获到API响应，将使用题库匹配")

            return True

        except Exception as e:
            logger.error(f"❌ 处理确认弹窗失败: {str(e)}")
            return False

    def answer_current_question(self) -> bool:
        """
        回答当前题目

        Returns:
            bool: 是否成功回答
        """
        try:
            logger.info("=" * 60)
            logger.info("📝 开始处理当前题目")

            # 解析当前题目
            question = self._parse_current_question()
            if not question:
                logger.error("❌ 解析题目失败")
                return False

            logger.info(f"   题目类型: {question['type_name']}")
            logger.info(f"   题目内容: {question['title'][:80]}...")
            logger.info(f"   选项数量: {len(question['options'])}")

            # 优先从API数据中查找答案（如果有）
            correct_values = None
            if self.current_api_question_ids:
                logger.info("🔍 尝试从API数据中查找答案...")
                correct_values = self._find_answer_from_api(question)

            # 如果API数据中没有找到，再从题库中查找
            if not correct_values:
                logger.info("🔍 从题库中查找答案...")
                correct_values = self._find_answer_in_bank(question)

            if not correct_values:
                logger.warning("⚠️ 未找到答案，跳过该题")
                return False

            # 根据题目类型选择答案
            if question['type'] in ["single", "judge"]:
                success = self._select_single_answer(question, correct_values)
            elif question['type'] == "multiple":
                success = self._select_multiple_answers(question, correct_values)
            else:
                logger.error(f"❌ 未知的题目类型: {question['type']}")
                return False

            if success:
                logger.info("✅ 题目回答完成")
            else:
                logger.error("❌ 题目回答失败")

            logger.info("=" * 60)
            return success

        except Exception as e:
            logger.error(f"❌ 回答题目失败: {str(e)}")
            return False

    def wait_for_completion_or_next(self, is_last_question: bool = False) -> bool:
        """
        等待题目完成后点击下一题

        Args:
            is_last_question: 是否是最后一题

        Returns:
            bool: 是否成功进入下一题或完成
        """
        try:
            if is_last_question:
                # 最后一题：点击下一题结束知识点，然后等待自动跳转
                logger.info("📝 最后一题，点击下一题结束知识点...")

                try:
                    next_button = self._get_page().wait_for_selector("button:has-text('下一题')", timeout=5000)
                    next_button.click()
                    logger.info("✅ 已点击下一题按钮，结束知识点")
                    time.sleep(1)
                except Exception:
                    logger.warning("⚠️ 未找到下一题按钮")

                # 等待检测成功提示
                logger.info("⏳ 等待考评成功提示（最多10秒）...")
                start_time = time.time()
                success_detected = False

                while time.time() - start_time < 10:
                    try:
                        # 检查是否有成功提示
                        success_element = self._get_page().query_selector(".eva-success")
                        if success_element and not success_detected:
                            logger.info("✅ 检测到成功提示：恭喜你,本次考评成功")
                            logger.info("⏳ 等待5秒自动跳转到下一个知识点...")
                            success_detected = True
                            break

                        time.sleep(0.5)
                    except Exception:
                        time.sleep(0.5)

                if success_detected:
                    # 等待5秒倒计时+1秒缓冲
                    time.sleep(6)

                    # 检测是否成功跳转：答题页面元素应该消失
                    logger.info("🔍 检测是否跳转到知识点列表...")

                    # 方法1：检测答题页面元素是否消失
                    try:
                        # 等待答题页面的题目类型元素消失
                        self._get_page().wait_for_selector(".question-type", state="hidden", timeout=3000)
                        logger.info("✅ 答题页面已消失，确认跳转成功")
                        return True
                    except Exception:
                        logger.debug("⚠️ .question-type 元素仍然存在")

                    # 方法2：检测是否可以找到"开始测评"按钮（知识点列表的特征）
                    try:
                        start_button = self._get_page().query_selector("button:has-text('开始测评')", timeout=2000)
                        if start_button:
                            logger.info("✅ 检测到'开始测评'按钮，确认已回到知识点列表")
                            return True
                    except Exception:
                        logger.debug("⚠️ 未找到'开始测评'按钮")

                    # 方法3：检测知识点菜单项是否存在
                    try:
                        menu_items = self._get_page().query_selector_all(".el-menu-item")
                        if len(menu_items) > 0:
                            logger.info(f"✅ 检测到 {len(menu_items)} 个知识点菜单项，已回到知识点列表")
                            return True
                    except Exception:
                        pass

                    logger.warning("⚠️ 无法确定是否成功跳转，但继续执行")
                    return True
                else:
                    logger.warning("⚠️ 超时未检测到成功提示，但继续执行")
                    return True

            else:
                # 不是最后一题：立即点击下一题进入下一题
                logger.info("➡️ 点击下一题进入下一题...")
                time.sleep(0.5)  # 稍微等待一下，让题目内容稳定

                try:
                    next_button = self._get_page().wait_for_selector("button:has-text('下一题')", timeout=5000)
                    next_button.click()
                    logger.info("✅ 已点击下一题按钮")
                    time.sleep(1.5)  # 等待下一题加载
                    return True
                except Exception as e:
                    logger.error(f"❌ 点击下一题按钮失败: {str(e)}")
                    return False

        except Exception as e:
            logger.error(f"❌ 等待完成失败: {str(e)}")
            return False

    def _answer_loop(self, max_questions: int = 5) -> Dict:
        """
        内部方法：只负责答题循环，不处理开始按钮

        Args:
            max_questions: 最多做题数量

        Returns:
            Dict: 做题结果统计
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

            # 等待答题界面加载
            time.sleep(2)

            # 循环做题
            for i in range(max_questions):
                # 检查是否需要停止（在每道题开始前）
                if self._check_stop():
                    self._is_processing_knowledge = False
                    return result

                # 标记正在答题
                self._is_answering_question = True

                logger.info(f"\n📌 第 {i+1}/{max_questions} 题")

                # 更新当前题目索引
                self.current_question_index = i

                # 获取当前题目序号
                current_num = self.get_current_question_number()
                if current_num == 0:
                    logger.warning("⚠️ 无法获取当前题目序号")

                # 回答当前题目
                success = self.answer_current_question()
                result['total'] += 1

                if success:
                    result['success'] += 1
                else:
                    result['failed'] += 1

                # 标记答题完成
                self._is_answering_question = False

                # 检查是否需要停止（每道题完成后）
                if self._check_stop():
                    self._is_processing_knowledge = False
                    return result

                # 等待完成或进入下一题
                is_last = (i == max_questions - 1)  # 是否是最后一题
                self.wait_for_completion_or_next(is_last_question=is_last)

            # 标记知识点处理完成
            self._is_processing_knowledge = False

            logger.info("=" * 60)
            logger.info("✅ 当前知识点做题流程完成")
            logger.info(f"📊 统计: 总计 {result['total']} 题, 成功 {result['success']} 题, 失败 {result['failed']} 题, 跳过 {result['skipped']} 题")

            return result

        except Exception as e:
            logger.error(f"❌ 答题循环失败: {str(e)}")
            self._is_answering_question = False
            self._is_processing_knowledge = False
            return result

    def run_auto_answer(self, max_questions: int = 5) -> Dict:
        """
        运行自动做题流程（第一个知识点：会检索并点击开始按钮）
        此方法会自动在工作线程中执行

        Args:
            max_questions: 最多做题数量

        Returns:
            Dict: 做题结果统计
            {
                'total': int,  # 总题数
                'success': int,  # 成功题数
                'failed': int,  # 失败题数
                'skipped': int,  # 跳过题数
                'stopped': bool  # 用户是否停止
            }
        """
        # 使用工作线程包装器确保所有 Playwright 操作都在工作线程中执行
        from src.core.browser import run_in_thread_if_asyncio
        return run_in_thread_if_asyncio(self._run_auto_answer_impl, max_questions)

    def _run_auto_answer_impl(self, max_questions: int = 5) -> Dict:
        """
        运行自动做题流程的实际实现（内部方法）

        Args:
            max_questions: 最多做题数量

        Returns:
            Dict: 做题结果统计
        """
        result = {
            'total': 0,
            'success': 0,
            'failed': 0,
            'skipped': 0,
            'stopped': False
        }

        try:
            # 检查浏览器是否存活
            if not self._check_page_alive():
                logger.error("❌ 浏览器已挂掉，无法继续做题")
                result['stopped'] = True
                return result

            logger.info("🚀 开始自动做题流程（第一个知识点）")
            logger.info("=" * 60)

            # 启动API监听器（在点击开始测评之前）
            self.start_api_listener()

            # 点击开始测评按钮（会自动查找可作答的知识点）
            if not self.click_start_button():
                logger.error("❌ 点击开始测评按钮失败")
                return result

            # 处理确认弹窗
            if not self.handle_confirm_dialog():
                logger.error("❌ 处理确认弹窗失败")
                return result

            # 调用答题循环
            result = self._answer_loop(max_questions)

            # 停止监听
            self.stop_api_listener()

            return result

        except Exception as e:
            logger.error(f"❌ 自动做题流程失败: {str(e)}")
            self.stop_api_listener()
            return result

    def continue_auto_answer(self, max_questions: int = 5) -> Dict:
        """
        继续自动做题流程（后续知识点：不检索，直接做题）
        用于网站自动跳转后继续做题
        此方法会自动在工作线程中执行

        Args:
            max_questions: 最多做题数量

        Returns:
            Dict: 做题结果统计
            {
                'total': int,  # 总题数
                'success': int,  # 成功题数
                'failed': int,  # 失败题数
                'skipped': int,  # 跳过题数
                'stopped': bool  # 用户是否停止
            }
        """
        # 使用工作线程包装器确保所有 Playwright 操作都在工作线程中执行
        from src.core.browser import run_in_thread_if_asyncio
        return run_in_thread_if_asyncio(self._continue_auto_answer_impl, max_questions)

    def _continue_auto_answer_impl(self, max_questions: int = 5) -> Dict:
        """
        继续自动做题流程的实际实现（内部方法）

        Args:
            max_questions: 最多做题数量

        Returns:
            Dict: 做题结果统计
        """
        result = {
            'total': 0,
            'success': 0,
            'failed': 0,
            'skipped': 0,
            'stopped': False
        }

        try:
            # 检查浏览器是否存活
            if not self._check_page_alive():
                logger.error("❌ 浏览器已挂掉，无法继续做题")
                result['stopped'] = True
                return result

            logger.info("🚀 继续自动做题流程（网站已自动跳转）")
            logger.info("=" * 60)

            # 启动API监听器（在点击开始测评之前）
            self.start_api_listener()

            # 先尝试直接点击当前页面的"开始测评"按钮（快速路径）
            logger.info("🎯 尝试直接点击当前页面的开始测评按钮...")
            if self.click_start_button_only():
                # 成功点击，直接开始做题
                logger.info("✅ 当前页面有可作答的知识点")
            else:
                # 没有找到"开始测评"按钮，说明跳转到的知识点已完成
                # 需要检索下一个未完成的知识点
                logger.info("⚠️ 当前页面没有可作答的知识点（可能已完成）")
                logger.info("🔍 开始检索下一个未完成的知识点...")

                # 等待页面稳定，可能页面还在加载中
                logger.info("⏳ 等待2秒让页面完全加载...")
                time.sleep(2)

                # 尝试检索（带重试）
                max_retries = 2
                found = False
                for retry in range(max_retries):
                    if retry > 0:
                        logger.info(f"🔄 第{retry + 1}次尝试检索...")

                    if self.click_start_button():
                        found = True
                        break

                    if retry < max_retries - 1:
                        logger.info("⏳ 等待3秒后重试...")
                        time.sleep(3)

                if not found:
                    logger.error("❌ 检索失败，未找到可作答的知识点，可能所有知识点都已完成")
                    return result

            # 处理确认弹窗
            if not self.handle_confirm_dialog():
                logger.error("❌ 处理确认弹窗失败")
                return result

            # 调用答题循环
            result = self._answer_loop(max_questions)

            # 停止监听
            self.stop_api_listener()

            return result

        except Exception as e:
            logger.error(f"❌ 继续做题流程失败: {str(e)}")
            self.stop_api_listener()
            return result

    def has_next_knowledge(self) -> bool:
        """
        检查是否还有下一个可作答的知识点
        通过检测页面上是否有"开始测评"按钮来判断
        此方法会自动在工作线程中执行

        Returns:
            bool: True表示还有更多知识点，False表示已完成
        """
        # 使用工作线程包装器确保所有 Playwright 操作都在工作线程中执行
        from src.core.browser import run_in_thread_if_asyncio
        return run_in_thread_if_asyncio(self._has_next_knowledge_impl)

    def _has_next_knowledge_impl(self) -> bool:
        """
        检查是否还有下一个可作答的知识点（实际实现）

        Returns:
            bool: True表示还有更多知识点，False表示已完成
        """
        try:
            page = self._get_page()
            if not page:
                return False

            # 尝试查找"开始测评"按钮
            try:
                page.wait_for_selector("button:has-text('开始测评')", timeout=3000)
                logger.debug("✅ 检测到下一个知识点")
                return True
            except Exception:
                # 没找到，说明所有知识点都完成了
                logger.debug("⚠️ 未检测到下一个知识点，可能已完成")
                return False

        except Exception as e:
            logger.error(f"❌ 检查下一个知识点失败: {str(e)}")
            return False

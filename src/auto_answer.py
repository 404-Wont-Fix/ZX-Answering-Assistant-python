"""
自动做题模块
用于在学生端自动作答题目
"""

from typing import Dict, List, Optional, Tuple
import html
import re
import time
import logging
import threading
import sys

logger = logging.getLogger(__name__)


class AutoAnswer:
    """自动做题类"""

    def __init__(self, page):
        """
        初始化自动做题器

        Args:
            page: Playwright页面对象
        """
        self.page = page
        self.question_bank = None  # 题库数据
        self.should_stop = False  # 停止标志
        self.input_thread = None  # 输入监听线程

    def load_question_bank(self, question_bank_data: Dict):
        """
        加载题库数据

        Args:
            question_bank_data: 题库数据（从JSON文件导入）
        """
        self.question_bank = question_bank_data
        logger.info("✅ 题库数据已加载")

    def _listen_for_stop(self):
        """
        监听用户输入，检测是否要停止
        在单独的线程中运行
        """
        try:
            while True:
                # 非阻塞检测用户输入
                # Windows下使用msvcrt，其他平台使用select
                try:
                    import msvcrt
                    if msvcrt.kbhit():  # 检测是否有键盘输入
                        char = msvcrt.getch().decode('utf-8')
                        if char.lower() == 'q':
                            print("\n\n⚠️  检测到停止信号，将在完成当前知识点后退出...")
                            logger.info("⚠️  用户请求停止做题")
                            self.should_stop = True
                            break
                except ImportError:
                    # 非Windows平台，使用input阻塞（简化处理）
                    # 这种情况下用户需要按回车
                    pass
                except:
                    pass

                time.sleep(0.1)  # 避免CPU占用过高

                if self.should_stop:
                    break
        except Exception as e:
            logger.debug(f"监听线程异常: {str(e)}")

    def start_stop_listener(self):
        """启动停止监听线程"""
        self.should_stop = False
        self.input_thread = threading.Thread(target=self._listen_for_stop, daemon=True)
        self.input_thread.start()
        logger.info("✅ 停止监听已启动（按 'q' 键可随时停止）")

    def stop_stop_listener(self):
        """停止停止监听线程"""
        self.should_stop = True
        if self.input_thread and self.input_thread.is_alive():
            self.input_thread.join(timeout=1)
        logger.info("✅ 停止监听已停止")

    def _normalize_text(self, text: str) -> str:
        """
        标准化文本，用于匹配

        Args:
            text: 原始文本

        Returns:
            str: 标准化后的文本
        """
        if not text:
            return ""

        # 解码HTML实体
        text = html.unescape(text)

        # 移除多余的空白字符
        text = re.sub(r'\s+', ' ', text)

        # 移除常见的HTML标签
        text = re.sub(r'<[^>]+>', '', text)

        # 移除特殊字符（保留中文、英文、数字、常用标点）
        # 使用Unicode编码表示方括号，避免转义序列警告：[ = \u005b, ] = \u005d
        pattern = r'[^\u4e00-\u9fa5a-zA-Z0-9\s\.,;:!?()（）【】《》、""\'\u005b\u005d]'
        text = re.sub(pattern, '', text)

        return text.strip()

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
            type_element = self.page.query_selector(".question-type")
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
            title_element = self.page.query_selector(".question-title")
            if not title_element:
                logger.error("❌ 未找到题目标题元素")
                return None

            title_text = title_element.text_content()
            title_normalized = self._normalize_text(title_text)

            # 获取选项
            options = []

            if question_type in ["single", "judge"]:
                # 单选或判断题 - 使用 el-radio
                radio_labels = self.page.query_selector_all(".el-radio")
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
                checkbox_labels = self.page.query_selector_all(".el-checkbox")
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

    def _find_answer_in_bank(self, question: Dict) -> Optional[List[str]]:
        """
        在题库中查找匹配的答案

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

            # 遍历题库查找匹配的题目
            chapters = []
            if "class" in self.question_bank and "course" in self.question_bank["class"]:
                # 单课程题库
                chapters = self.question_bank["class"]["course"].get("chapters", [])
            elif "chapters" in self.question_bank:
                # 多课程题库
                chapters = self.question_bank["chapters"]

            for chapter in chapters:
                knowledges = chapter.get("knowledges", [])
                for knowledge in knowledges:
                    questions = knowledge.get("questions", [])
                    for bank_question in questions:
                        # 标准化题库中的题目标题
                        bank_title = self._normalize_text(bank_question.get("QuestionTitle", ""))

                        # 匹配题目（使用模糊匹配）
                        if self._match_question(question_title, bank_title):
                            logger.info(f"✅ 在题库中找到匹配的题目")
                            logger.info(f"   题目: {question_title[:50]}...")

                            # 获取正确答案
                            options = bank_question.get("options", [])
                            correct_values = []

                            for option in options:
                                if option.get("isTrue", False):
                                    correct_values.append(option.get("id", ""))

                            if correct_values:
                                logger.info(f"   正确答案: {len(correct_values)} 个选项")
                                return correct_values
                            else:
                                logger.warning(f"⚠️ 题库中该题目没有标记正确答案")
                                return None

            logger.warning(f"⚠️ 未在题库中找到匹配的题目")
            logger.info(f"   当前题目: {question_title[:100]}...")
            return None

        except Exception as e:
            logger.error(f"❌ 在题库中查找答案失败: {str(e)}")
            return None

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
            return True

        # 包含匹配（一个包含另一个）
        if question1 in question2 or question2 in question1:
            return True

        # 移除标点和空格后匹配
        q1_clean = re.sub(r'[^\w\u4e00-\u9fa5]', '', question1)
        q2_clean = re.sub(r'[^\w\u4e00-\u9fa5]', '', question2)

        if q1_clean == q2_clean:
            return True

        return False

    def _select_single_answer(self, question: Dict, correct_values: List[str]) -> bool:
        """
        选择单选题/判断题的答案

        Args:
            question: 题目信息
            correct_values: 正确选项的value列表

        Returns:
            bool: 是否成功选择
        """
        try:
            if not correct_values:
                logger.error("❌ 没有正确答案")
                return False

            correct_value = correct_values[0]  # 单选题只有一个正确答案

            # 查找对应的选项并点击
            for option in question['options']:
                if option['value'] == correct_value:
                    # 点击选项
                    option_label = option['label']
                    logger.info(f"   选择答案: {option_label}")

                    # 点击label元素而不是input元素（Element UI的组件需要点击label）
                    if question['type'] == "judge":
                        # 判断题 - 点击包含该value的label
                        selector = f".el-radio:has(input[value='{correct_value}'])"
                    else:
                        # 单选题 - 点击包含该value的label
                        selector = f".el-radio:has(input[value='{correct_value}'])"

                    self.page.click(selector, timeout=10000)
                    time.sleep(0.5)  # 等待选择完成
                    return True

            logger.error(f"❌ 未找到value为 {correct_value} 的选项")
            return False

        except Exception as e:
            logger.error(f"❌ 选择单选答案失败: {str(e)}")
            return False

    def _select_multiple_answers(self, question: Dict, correct_values: List[str]) -> bool:
        """
        选择多选题的答案

        Args:
            question: 题目信息
            correct_values: 正确选项的value列表

        Returns:
            bool: 是否成功选择
        """
        try:
            if not correct_values:
                logger.error("❌ 没有正确答案")
                return False

            selected_count = 0

            # 查找对应的选项并点击
            for correct_value in correct_values:
                for option in question['options']:
                    if option['value'] == correct_value:
                        # 点击选项
                        option_label = option['label']
                        option_content = option['content'][:30]
                        logger.info(f"   选择答案: {option_label} - {option_content}...")

                        # 点击label元素而不是input元素（Element UI的组件需要点击label）
                        selector = f".el-checkbox:has(input[value='{correct_value}'])"
                        self.page.click(selector, timeout=10000)
                        selected_count += 1

                        # 延迟，防止点击过快导致选择失败
                        time.sleep(0.3)
                        break

            if selected_count == len(correct_values):
                logger.info(f"✅ 成功选择 {selected_count} 个答案")
                return True
            else:
                logger.warning(f"⚠️ 只选择了 {selected_count}/{len(correct_values)} 个答案")
                return False

        except Exception as e:
            logger.error(f"❌ 选择多选答案失败: {str(e)}")
            return False

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
            self.page.reload(wait_until="networkidle")
            time.sleep(2)  # 等待页面完全加载
            logger.info("✅ 网页刷新完成")

            # 等待知识点列表加载
            self.page.wait_for_selector(".el-submenu", timeout=5000)

            # 获取所有章节（折叠菜单）
            chapters = self.page.query_selector_all(".el-submenu")

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
                    for item in knowledge_items:
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
                                start_button = self.page.query_selector("button:has-text('开始测评')", timeout=1000)
                                if start_button:
                                    logger.info(f"✅ 找到可作答知识点: {knowledge_name}")
                                    return True
                            except:
                                pass

                            # 方法2: 查找"第X次测评"
                            if not start_button:
                                try:
                                    buttons = self.page.query_selector_all("button.el-button--primary")
                                    for btn in buttons:
                                        text = btn.text_content() or ""
                                        if "测评" in text:
                                            start_button = btn
                                            logger.info(f"✅ 找到可作答知识点: {knowledge_name} (按钮: {text.strip()})")
                                            return True
                                except:
                                    pass

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

            # 尝试查找"开始测评"按钮
            start_button = None

            # 方法1: 查找包含"开始测评"文本的按钮
            try:
                start_button = self.page.wait_for_selector("button:has-text('开始测评')", timeout=3000)
                logger.info("✅ 找到'开始测评'按钮")
            except:
                logger.info("⚠️ 未找到'开始测评'按钮，尝试查找'第X次测评'按钮")

            # 方法2: 查找包含"测评"文本的按钮（可能是重做）
            if not start_button:
                try:
                    buttons = self.page.query_selector_all("button.el-button--primary")
                    for btn in buttons:
                        text = btn.text_content()
                        if "测评" in text:
                            start_button = btn
                            logger.info(f"✅ 找到测评按钮: {text.strip()}")
                            break
                except:
                    pass

            if not start_button:
                logger.error("❌ 未找到开始测评按钮，可能所有知识点都已完成")
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
                start_button = self.page.wait_for_selector("button:has-text('开始测评')", timeout=2000)
                logger.info("✅ 找到'开始测评'按钮")
            except:
                logger.info("⚠️ 未找到'开始测评'按钮，尝试查找'第X次测评'按钮")

            # 方法2: 查找包含"测评"文本的按钮（可能是重做）
            if not start_button:
                try:
                    buttons = self.page.query_selector_all("button.el-button--primary")
                    for btn in buttons:
                        text = btn.text_content()
                        if "测评" in text:
                            start_button = btn
                            logger.info(f"✅ 找到测评按钮: {text.strip()}")
                            break
                except:
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
                dialog = self.page.wait_for_selector(".el-message-box", timeout=5000)
                if dialog:
                    dialog_found = True
                    logger.info("✅ 检测到确认弹窗")
            except:
                logger.info("⚠️ 未检测到确认弹窗，可能已经进入答题界面")
                return True

            if not dialog_found:
                return True

            # 多种方法查找"确定"按钮
            confirm_button = None

            # 方法1: 在弹窗内查找主要按钮
            try:
                confirm_button = self.page.wait_for_selector(".el-message-box button.el-button--primary", timeout=2000)
                logger.info("✅ 方法1: 找到确定按钮")
            except:
                logger.debug("⚠️ 方法1未找到")

            # 方法2: 查找包含"确定"文本的按钮
            if not confirm_button:
                try:
                    buttons = self.page.query_selector_all(".el-message-box button")
                    for btn in buttons:
                        text = btn.text_content() or ""
                        if "确定" in text:
                            confirm_button = btn
                            logger.info("✅ 方法2: 找到确定按钮")
                            break
                except:
                    logger.debug("⚠️ 方法2未找到")

            # 方法3: 使用CSS选择器查找第二个按钮（确定按钮通常在第二个位置）
            if not confirm_button:
                try:
                    buttons = self.page.query_selector_all(".el-message-box__btns button")
                    if len(buttons) >= 2:
                        confirm_button = buttons[1]  # 第二个按钮通常是"确定"
                        logger.info("✅ 方法3: 找到确定按钮（第二个按钮）")
                except:
                    logger.debug("⚠️ 方法3未找到")

            if not confirm_button:
                logger.error("❌ 未找到确定按钮")
                return False

            # 点击确定
            confirm_button.click()
            logger.info("✅ 已点击确定按钮")

            # 等待答题界面加载
            time.sleep(2)
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

            # 在题库中查找答案
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
                    next_button = self.page.wait_for_selector("button:has-text('下一题')", timeout=5000)
                    next_button.click()
                    logger.info("✅ 已点击下一题按钮，结束知识点")
                    time.sleep(1)
                except:
                    logger.warning("⚠️ 未找到下一题按钮")

                # 等待检测成功提示
                logger.info("⏳ 等待考评成功提示（最多10秒）...")
                start_time = time.time()
                success_detected = False

                while time.time() - start_time < 10:
                    try:
                        # 检查是否有成功提示
                        success_element = self.page.query_selector(".eva-success")
                        if success_element and not success_detected:
                            logger.info("✅ 检测到成功提示：恭喜你,本次考评成功")
                            logger.info("⏳ 等待5秒自动跳转到下一个知识点...")
                            success_detected = True
                            break

                        time.sleep(0.5)
                    except:
                        time.sleep(0.5)

                if success_detected:
                    # 等待5秒倒计时+1秒缓冲
                    time.sleep(6)

                    # 检测是否成功跳转：答题页面元素应该消失
                    logger.info("🔍 检测是否跳转到知识点列表...")

                    # 方法1：检测答题页面元素是否消失
                    try:
                        # 等待答题页面的题目类型元素消失
                        self.page.wait_for_selector(".question-type", state="hidden", timeout=3000)
                        logger.info("✅ 答题页面已消失，确认跳转成功")
                        return True
                    except:
                        logger.debug("⚠️ .question-type 元素仍然存在")

                    # 方法2：检测是否可以找到"开始测评"按钮（知识点列表的特征）
                    try:
                        start_button = self.page.query_selector("button:has-text('开始测评')", timeout=2000)
                        if start_button:
                            logger.info("✅ 检测到'开始测评'按钮，确认已回到知识点列表")
                            return True
                    except:
                        logger.debug("⚠️ 未找到'开始测评'按钮")

                    # 方法3：检测知识点菜单项是否存在
                    try:
                        menu_items = self.page.query_selector_all(".el-menu-item")
                        if len(menu_items) > 0:
                            logger.info(f"✅ 检测到 {len(menu_items)} 个知识点菜单项，已回到知识点列表")
                            return True
                    except:
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
                    next_button = self.page.wait_for_selector("button:has-text('下一题')", timeout=5000)
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

    def get_current_question_number(self) -> int:
        """
        获取当前题目序号

        Returns:
            int: 当前题目序号（1-5），如果获取失败返回0
        """
        try:
            # 查找所有题目序号元素
            question_items = self.page.query_selector_all(".question-item")

            for i, item in enumerate(question_items, 1):
                # 检查是否有"selected"类
                class_attr = item.get_attribute("class") or ""
                if "selected" in class_attr:
                    logger.info(f"📍 当前题目序号: {i}/{len(question_items)}")
                    return i

            # 如果没有找到selected，返回0
            return 0

        except Exception as e:
            logger.error(f"❌ 获取当前题目序号失败: {str(e)}")
            return 0

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
            # 等待答题界面加载
            time.sleep(2)

            # 循环做题
            for i in range(max_questions):
                logger.info(f"\n📌 第 {i+1}/{max_questions} 题")

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

                # 等待完成或进入下一题
                is_last = (i == max_questions - 1)  # 是否是最后一题
                self.wait_for_completion_or_next(is_last_question=is_last)

            logger.info("=" * 60)
            logger.info("✅ 当前知识点做题流程完成")
            logger.info(f"📊 统计: 总计 {result['total']} 题, 成功 {result['success']} 题, 失败 {result['failed']} 题, 跳过 {result['skipped']} 题")

            return result

        except Exception as e:
            logger.error(f"❌ 答题循环失败: {str(e)}")
            return result

    def run_auto_answer(self, max_questions: int = 5) -> Dict:
        """
        运行自动做题流程（第一个知识点：会检索并点击开始按钮）

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
        result = {
            'total': 0,
            'success': 0,
            'failed': 0,
            'skipped': 0,
            'stopped': False
        }

        try:
            logger.info("🚀 开始自动做题流程（第一个知识点）")
            logger.info("=" * 60)

            # 启动停止监听
            self.start_stop_listener()
            print("💡 提示：按 'q' 键可随时停止做题（将在完成当前知识点后退出）")

            # 点击开始测评按钮（会自动查找可作答的知识点）
            if not self.click_start_button():
                logger.error("❌ 点击开始测评按钮失败")
                self.stop_stop_listener()
                return result

            # 处理确认弹窗
            if not self.handle_confirm_dialog():
                logger.error("❌ 处理确认弹窗失败")
                self.stop_stop_listener()
                return result

            # 调用答题循环
            result = self._answer_loop(max_questions)

            # 检查是否用户请求停止
            if self.should_stop:
                result['stopped'] = True
                logger.info("⚠️  用户请求停止，不做下一个知识点")
            else:
                result['stopped'] = False

            # 停止监听
            self.stop_stop_listener()

            return result

        except Exception as e:
            logger.error(f"❌ 自动做题流程失败: {str(e)}")
            self.stop_stop_listener()
            return result

    def continue_auto_answer(self, max_questions: int = 5) -> Dict:
        """
        继续自动做题流程（后续知识点：不检索，直接做题）
        用于网站自动跳转后继续做题

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
        result = {
            'total': 0,
            'success': 0,
            'failed': 0,
            'skipped': 0,
            'stopped': False
        }

        try:
            logger.info("🚀 继续自动做题流程（网站已自动跳转）")
            logger.info("=" * 60)

            # 启动停止监听
            self.start_stop_listener()
            print("💡 提示：按 'q' 键可随时停止做题（将在完成当前知识点后退出）")

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

                if not self.click_start_button():
                    logger.error("❌ 检索失败，未找到可作答的知识点")
                    self.stop_stop_listener()
                    return result

            # 处理确认弹窗
            if not self.handle_confirm_dialog():
                logger.error("❌ 处理确认弹窗失败")
                self.stop_stop_listener()
                return result

            # 调用答题循环
            result = self._answer_loop(max_questions)

            # 检查是否用户请求停止
            if self.should_stop:
                result['stopped'] = True
                logger.info("⚠️  用户请求停止，不做下一个知识点")
            else:
                result['stopped'] = False

            # 停止监听
            self.stop_stop_listener()

            return result

        except Exception as e:
            logger.error(f"❌ 继续做题流程失败: {str(e)}")
            self.stop_stop_listener()
            return result

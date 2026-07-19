"""
答题基类

提供 AutoAnswer（学生端）和 CourseAutoAnswer（课程认证）共享的通用答题方法。
"""

import time
from abc import ABC, abstractmethod
from typing import Dict, List


class BaseAnswer(ABC):
    """答题基类，子类需实现 _get_page()"""

    @abstractmethod
    def _get_page(self):
        """返回当前 Playwright Page 对象"""
        ...

    def _select_single_answer(self, question: Dict, correct_values: List[str]) -> bool:
        """选择单选答案"""
        try:
            if not correct_values:
                print("❌ 没有正确答案")
                return False

            correct_value = correct_values[0]

            # 在选项中查找匹配的值
            for option in question['options']:
                if option['value'] == correct_value:
                    option_label = option['label']
                    print(f"   选择答案: {option_label}")

                    # 点击对应的单选按钮
                    selector = f".el-radio:has(input[value='{correct_value}'])"
                    self._get_page().click(selector, timeout=10000)
                    time.sleep(0.5)
                    return True

            print(f"❌ 未找到value为 {correct_value} 的选项")
            return False

        except Exception as e:
            print(f"❌ 选择单选答案失败: {str(e)}")
            return False

    def _select_multiple_answers(self, question: Dict, correct_values: List[str]) -> bool:
        """选择多选答案"""
        try:
            if not correct_values:
                print("❌ 没有正确答案")
                return False

            print(f"   选择答案: {correct_values}")

            # 逐个点击所有正确选项，跟踪是否全部匹配
            matched_count = 0
            for correct_value in correct_values:
                for option in question['options']:
                    if option['value'] == correct_value:
                        selector = f".el-checkbox:has(input[value='{correct_value}'])"
                        self._get_page().click(selector, timeout=10000)
                        time.sleep(0.3)
                        matched_count += 1
                        break
                else:
                    print(f"⚠️ 未找到value为 {correct_value} 的选项")

            # 若有正确值未匹配到选项，视为失败（避免漏选被计为成功）
            return matched_count == len(correct_values)

        except Exception as e:
            print(f"❌ 选择多选答案失败: {str(e)}")
            return False

    def get_current_question_number(self) -> int:
        """获取当前题目序号"""
        try:
            question_items = self._get_page().query_selector_all(".question-item")
            for i, item in enumerate(question_items, 1):
                class_attr = item.get_attribute("class") or ""
                if "selected" in class_attr:
                    print(f"📍 当前题目序号: {i}/{len(question_items)}")
                    return i
            return 0
        except Exception as e:
            print(f"❌ 获取当前题目序号失败: {str(e)}")
            return 0

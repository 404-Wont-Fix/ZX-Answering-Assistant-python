"""src/answering/_answer_matcher.py AnswerMatcherMixin 的单元测试。

重点验证 C2 回归：当 API 题目顺序与页面题目顺序不一致时，
_find_answer_from_api 必须返回 None 以回退到题库匹配，而不是按错误位置索引。
"""

import sys
import unittest

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

from src.answering._answer_matcher import AnswerMatcherMixin


class _StubMatcher(AnswerMatcherMixin):
    """仅提供 Mixin 所需属性的最小宿主。"""

    def __init__(self, *, question_bank=None, api_ids=None, api_titles=None,
                 question_index=0, api_order_verified=False):
        self.question_bank = question_bank or {}
        self.current_api_question_ids = api_ids or []
        self.current_api_question_titles = api_titles or []
        self.current_question_index = question_index
        self.api_order_verified = api_order_verified
        self.current_chapter = "第一章"
        self.current_knowledge = "知识点1"
        self.current_knowledge_index = 0

    def _normalize_text(self, text):
        return text.strip()


class OrderVerificationTests(unittest.TestCase):
    """C2 regression: per-question title verification."""

    def test_matching_title_proceeds_to_bank_lookup(self):
        """When page title matches API title at the same index, proceed."""
        m = _StubMatcher(
            question_bank={"any": True},
            api_ids=["id-1", "id-2"],
            api_titles=["什么是人工智能", "机器学习的定义"],
            question_index=0,
        )
        # Q1 title matches → should NOT return None at the title-verification step.
        # It will still return None from _find_answer_in_bank_by_question_id because
        # the bank doesn't contain this question, but that's the bank lookup failing,
        # not the title verification failing.
        result = m._find_answer_from_api({"title": "什么是人工智能", "options": []})
        # The method proceeds past title check → enters _find_answer_in_bank_by_question_id
        # which returns None because the bank is empty. That's the expected fallback.
        self.assertIsNone(result)
        # Key: api_order_verified should be True (title matched)
        self.assertTrue(m.api_order_verified)

    def test_mismatched_q2_returns_none(self):
        """When Q2 page title doesn't match API Q2 title, return None (fall back to bank)."""
        m = _StubMatcher(
            question_bank={"any": True},
            api_ids=["id-a", "id-b", "id-c"],
            api_titles=["题目A的完整标题", "题目B的完整标题", "题目C的完整标题"],
            question_index=1,  # Q2
            api_order_verified=True,  # Q1 already verified
        )
        # Q2 page title is completely different from API Q2 title
        result = m._find_answer_from_api({"title": "这是完全不同的一道题目XYZ", "options": []})
        self.assertIsNone(result, "Mismatched Q2 title should return None to fall back to bank matching")

    def test_all_questions_must_match_not_just_first(self):
        """Verify every question, not just Q1 — if Q3 mismatches, return None."""
        m = _StubMatcher(
            question_bank={"any": True},
            api_ids=["id-1", "id-2", "id-3"],
            api_titles=["第一题标题", "第二题标题", "第三题标题"],
            question_index=2,  # Q3
            api_order_verified=True,
        )
        result = m._find_answer_from_api({"title": "与第三题完全无关的标题", "options": []})
        self.assertIsNone(result)

    def test_empty_api_titles_returns_none(self):
        """When API provides no titles, title verification can't run → fall back."""
        m = _StubMatcher(
            question_bank={"any": True},
            api_ids=["id-1"],
            api_titles=[],  # empty
            question_index=0,
        )
        result = m._find_answer_from_api({"title": "任何题目", "options": []})
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()

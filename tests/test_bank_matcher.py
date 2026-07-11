"""src/utils/bank_matcher.py 的单元测试。

锁定三处纯 API 答题模式（学生端 src/answering/api_answer、认证端
src/certification/api_answer、云考试 plugins/cloud_exam/workflow）共享的
"按题目 ID 精确匹配 + 返回正确选项 ID"行为，供重构后回归。
"""

import unittest

from src.utils.bank_matcher import find_correct_answer_ids


# ---------- 题库构造 helpers ----------

def _knowledge(questions, name="k1"):
    return {"KnowledgeID": name, "Knowledge": "知识点-" + name, "questions": questions}


def _chapter(knowledges, cid="c1"):
    return {"chapterID": cid, "chapterTitle": "章节-" + cid, "knowledges": knowledges}


def _question(qid, correct_ids, *, qid_field="QuestionID", extra_options=None):
    """构造一道题目。correct_ids 给出正确选项 id 列表；自动追加一个错误选项。

    extra_options 可传入完整选项 dict 列表（用于测试 answerID/缺 id 等场景）。
    """
    if extra_options is not None:
        options = extra_options
    else:
        options = [{"id": cid, "isTrue": True} for cid in correct_ids]
        options.append({"id": "wrong", "isTrue": False})
    q = {"QuestionTitle": "title-of-" + str(qid), "options": options}
    q[qid_field] = qid
    return q


def _bank_top_chapters(chapters):
    return {"chapters": chapters}


def _bank_single_course(chapters):
    return {"class": {"course": {"chapters": chapters}}}


def _bank_courses(chapters):
    return {"courses": [{"courseID": "course-1", "chapters": chapters}]}


def _bank_course_list(chapters):
    return {"course_list": [{"courseID": "course-1", "chapters": chapters}]}


# ---------- 测试 ----------

class FindCorrectAnswerIdsStructureTests(unittest.TestCase):
    """4 种题库导出结构都能正确遍历命中。"""

    def _chapters_with(self, qid_field="QuestionID"):
        return [_chapter([_knowledge([_question("q1", ["a1"], qid_field=qid_field)])])]

    def test_finds_in_top_level_chapters(self):
        bank = _bank_top_chapters(self._chapters_with())
        self.assertEqual(find_correct_answer_ids(bank, "q1"), ["a1"])

    def test_finds_in_single_course_structure(self):
        bank = _bank_single_course(self._chapters_with())
        self.assertEqual(find_correct_answer_ids(bank, "q1"), ["a1"])

    def test_finds_in_multi_course_courses_structure(self):
        bank = _bank_courses(self._chapters_with())
        self.assertEqual(find_correct_answer_ids(bank, "q1"), ["a1"])

    def test_finds_in_multi_course_course_list_structure(self):
        bank = _bank_course_list(self._chapters_with())
        self.assertEqual(find_correct_answer_ids(bank, "q1"), ["a1"])


class FindCorrectAnswerIdsBehaviorTests(unittest.TestCase):
    """命中/未命中/多选/无正确选项等核心行为。"""

    def test_finds_multiple_correct_answers_preserving_order(self):
        bank = _bank_top_chapters(
            [_chapter([_knowledge([_question("q1", ["a1", "a2"])])])]
        )
        # 多选：按 options 顺序返回正确选项 id
        self.assertEqual(find_correct_answer_ids(bank, "q1"), ["a1", "a2"])

    def test_returns_none_when_question_id_not_found(self):
        bank = _bank_top_chapters(
            [_chapter([_knowledge([_question("q1", ["a1"])])])]
        )
        self.assertIsNone(find_correct_answer_ids(bank, "missing"))

    def test_returns_none_when_no_correct_option_marked(self):
        q = {"QuestionID": "q1", "QuestionTitle": "t", "options": [
            {"id": "a1", "isTrue": False},
            {"id": "a2", "isTrue": False},
        ]}
        bank = _bank_top_chapters([_chapter([_knowledge([q])])])
        # 命中题目但没有 isTrue 选项 → None
        self.assertIsNone(find_correct_answer_ids(bank, "q1"))

    def test_returns_none_when_empty_question_id(self):
        bank = _bank_top_chapters([_chapter([_knowledge([_question("q1", ["a1"])])])])
        self.assertIsNone(find_correct_answer_ids(bank, ""))
        self.assertIsNone(find_correct_answer_ids(bank, "   "))

    def test_returns_none_when_bank_empty_or_none(self):
        self.assertIsNone(find_correct_answer_ids({}, "q1"))
        self.assertIsNone(find_correct_answer_ids(None, "q1"))

    def test_strips_whitespace_around_question_id(self):
        bank = _bank_top_chapters([_chapter([_knowledge([_question("q1", ["a1"])])])])
        self.assertEqual(find_correct_answer_ids(bank, "  q1  "), ["a1"])


class FindCorrectAnswerIdsScopeTests(unittest.TestCase):
    """scope_knowledge 限定搜索范围（服务认证端 #5 的 knowledge 参数）。"""

    def setUp(self):
        self.kn_with_q = _knowledge([_question("q1", ["a1"])], name="kn-a")
        self.kn_without = _knowledge([_question("q2", ["a2"])], name="kn-b")
        self.bank = _bank_top_chapters([_chapter([self.kn_with_q, self.kn_without])])

    def test_scope命中当题目在该知识点内(self):
        self.assertEqual(
            find_correct_answer_ids(self.bank, "q1", scope_knowledge=self.kn_with_q),
            ["a1"],
        )

    def test_scope返回None当题目不在该知识点内(self):
        # 限定在 kn-b 内找 q1 → 找不到（即使全局有）
        self.assertIsNone(
            find_correct_answer_ids(self.bank, "q1", scope_knowledge=self.kn_without)
        )

    def test_global_search_finds_across_knowledges(self):
        # 不限定 scope 时全局搜索，两个知识点里的题都能命中
        self.assertEqual(find_correct_answer_ids(self.bank, "q1"), ["a1"])
        self.assertEqual(find_correct_answer_ids(self.bank, "q2"), ["a2"])


class FindCorrectAnswerIdsFieldCompatTests(unittest.TestCase):
    """题目ID字段名 / 选项ID字段名 / 空id过滤 的兼容性。"""

    def test_question_id_field_name_compat(self):
        # 4 种字段命名都能命中
        for field in ("QuestionID", "questionID", "question_id", "id"):
            with self.subTest(field=field):
                bank = _bank_top_chapters(
                    [_chapter([_knowledge([_question("q1", ["a1"], qid_field=field)])])]
                )
                self.assertEqual(find_correct_answer_ids(bank, "q1"), ["a1"])

    def test_option_id_field_compat(self):
        # 选项 id 用 answerID / AnswerID 也能提取
        options = [
            {"answerID": "by-answerID", "isTrue": True},
            {"AnswerID": "by-AnswerID", "isTrue": True},
            {"id": "by-id", "isTrue": True},
            {"id": "wrong", "isTrue": False},
        ]
        bank = _bank_top_chapters(
            [_chapter([_knowledge([_question("q1", [], extra_options=options)])])]
        )
        self.assertEqual(
            find_correct_answer_ids(bank, "q1"),
            ["by-answerID", "by-AnswerID", "by-id"],
        )

    def test_filters_out_correct_options_without_id(self):
        # isTrue 但缺 id 的选项不被返回（修正原 #3 的 append("") 空串 bug）
        options = [
            {"isTrue": True},            # 缺 id，应被过滤
            {"id": "a1", "isTrue": True},
            {"id": "", "isTrue": True},  # 空 id，应被过滤
            {"id": "wrong", "isTrue": False},
        ]
        bank = _bank_top_chapters(
            [_chapter([_knowledge([_question("q1", [], extra_options=options)])])]
        )
        self.assertEqual(find_correct_answer_ids(bank, "q1"), ["a1"])

    def test_option_id_is_stringified(self):
        # 非字符串 id（如 int）转 str
        options = [{"id": 123, "isTrue": True}, {"id": "wrong", "isTrue": False}]
        bank = _bank_top_chapters(
            [_chapter([_knowledge([_question("q1", [], extra_options=options)])])]
        )
        self.assertEqual(find_correct_answer_ids(bank, "q1"), ["123"])


if __name__ == "__main__":
    unittest.main()

"""
WeBan Module Adapter

This module provides an isolated adapter for the WeBan submodule,
ensuring code separation and independent functionality.
"""

import sys
import os
from pathlib import Path
import json
import threading
import subprocess
from typing import Optional, Callable, List, Dict, Any

def _find_weban_path() -> Optional[Path]:
    """
    查找 WeBan 模块路径

    按优先级查找以下位置：
    1. 插件 modules 目录：plugins/weban_plugin/modules/WeBan/
    2. 插件目录：plugins/weban_plugin/WeBan/
    3. 项目根目录：WeBan/
    4. Submodules 目录：submodules/WeBan/

    Returns:
        找到的 WeBan 路径，如果未找到返回 None
    """
    # 当前文件所在目录（插件根目录）
    current_dir = Path(__file__).parent

    # 可能的 WeBan 位置
    possible_paths = [
        # 1. 插件 modules 目录（推荐位置）
        current_dir / "modules" / "WeBan",
        # 2. 插件目录（自动设置后的位置）
        current_dir / "WeBan",
        # 3. 项目根目录（开发环境）
        current_dir.parent.parent / "WeBan",
        # 4. 作为 git submodule
        current_dir.parent.parent / "submodules" / "WeBan",
        # 5. 上一级目录
        current_dir.parent.parent.parent / "WeBan",
    ]

    for path in possible_paths:
        if path.exists() and (path / "api.py").exists():
            return path

    return None


# 自动查找并设置 WeBan 路径
weban_path = _find_weban_path()

if weban_path:
    if str(weban_path) not in sys.path:
        sys.path.insert(0, str(weban_path))
    try:
        from client import WeBanClient
        from api import WeBanAPI
        WEBAN_AVAILABLE = True
    except ImportError as e:
        print(f"⚠️ WeBan 模块导入失败: {e}")
        print(f"   WeBan路径: {weban_path}")
        print(f"   请确保WeBan依赖包已安装: pip install ddddocr loguru pycryptodome requests")
        WEBAN_AVAILABLE = False
        WeBanClient = None
        WeBanAPI = None
else:
    print("⚠️ 未找到 WeBan 模块")
    print("   WeBan 插件将不可用")
    print("   如需使用此插件，请确保 WeBan 项目存在")
    WEBAN_AVAILABLE = False
    WeBanClient = None
    WeBanAPI = None


class WeBanAdapter:
    """
    WeBan 模块适配器

    提供与主项目隔离的 WeBan 功能接口
    """

    def __init__(self, progress_callback: Optional[Callable[[str, str], None]] = None, input_callback: Optional[Callable[[str], str]] = None):
        """
        初始化适配器

        Args:
            progress_callback: 进度回调函数，参数 (message: str, level: str)
                level 可选值: "info", "success", "warning", "error"
            input_callback: 用户输入回调函数，参数 (prompt: str)，返回用户输入的字符串
                用于 GUI 模式下的验证码输入、手动答题等场景
        """
        self.progress_callback = progress_callback or self._default_callback
        self.input_callback = input_callback or self._default_input
        self.is_running = False
        self._stop_event = threading.Event()
        self._config: List[Dict[str, Any]] = []

        # 检查 WeBan 是否可用
        if not WEBAN_AVAILABLE:
            self._log("WeBan 模块不可用，插件功能受限", "warning")
            return

        # 应用 Monkey Patch 添加停止功能
        self._apply_stop_patch()
        # 应用 Monkey Patch 添加 GUI 输入支持
        self._apply_input_patch()

        # 保存 input_callback 的引用，供 monkey patch 使用
        try:
            WeBanClient._weban_adapter_input = self.input_callback
        except AttributeError as e:
            self._log(f"无法设置 WeBanClient 回调: {e}", "warning")

    def _default_callback(self, message: str, level: str = "info"):
        """默认进度回调"""
        prefix_map = {
            "info": "ℹ️",
            "success": "✅",
            "warning": "⚠️",
            "error": "❌",
        }
        print(f"{prefix_map.get(level, 'ℹ️')} {message}")

    def _default_input(self, prompt: str) -> str:
        """默认输入回调（CLI 模式）"""
        return input(prompt)

    def _log(self, message: str, level: str = "info"):
        """发送日志到回调"""
        try:
            self.progress_callback(message, level)
        except Exception as e:
            print(f"回调函数执行失败: {e}")
            self._default_callback(message, level)

    def check_available(self) -> bool:
        """检查 WeBan 模块是否可用"""
        return WEBAN_AVAILABLE

    def get_dependencies(self) -> List[str]:
        """获取 WeBan 模块依赖"""
        return [
            "ddddocr==1.6.1",
            "loguru==0.7.3",
            "pycryptodome==3.23.0",
            "requests==2.32.5",
        ]

    def _apply_stop_patch(self):
        """
        应用 Monkey Patch 添加停止功能

        通过动态替换 WeBanClient 的方法，在关键循环点注入停止检查
        """
        if not WEBAN_AVAILABLE:
            return

        # 使用类级别标志确保 Monkey Patch 只应用一次
        if not hasattr(WeBanClient, '_weban_patch_applied'):
            # 保存原始方法（只保存一次）
            WeBanClient._original_run_study = WeBanClient.run_study
            WeBanClient._original_run_exam = WeBanClient.run_exam

            # 创建带停止检查的包装方法
            def run_study_with_stop(self, study_time: int = 20, restudy_time: int = 0):
                """带停止检查的 run_study 方法"""
                # 检查是否设置了停止标志
                if hasattr(self, '_adapter') and hasattr(self._adapter, '_stop_event'):
                    if self._adapter._stop_event.is_set():
                        self._adapter._log("用户中断：学习阶段", "warning")
                        return

                # 调用原始方法的大部分逻辑，但在关键循环点检查停止
                if study_time:
                    self.study_time = study_time

                if restudy_time:
                    self.study_time = restudy_time
                    self.log.info(f"重新学习模式已开启，所有课程将重新学习，每门课程学习 {self.study_time} 秒")

                my_project = self.api.list_my_project()
                if my_project.get("code", -1) != "0":
                    self.log.error(f"获取任务列表失败：{my_project}")
                    return

                my_project = my_project.get("data", [])
                if not my_project:
                    self.log.error(f"获取任务列表失败")

                completion = self.api.list_completion()
                if completion.get("code", -1) != "0":
                    self.log.error(f"获取模块完成情况失败：{completion}")

                showable_modules = [d["module"] for d in completion.get("data", []) if d["showable"] == 1]
                if "labProject" in showable_modules:
                    self.log.info(f"加载实验室课程")
                    lab_project = self.api.lab_index()
                    if lab_project.get("code", -1) != "0":
                        self.log.error(f"获取实验室课程失败：{lab_project}")
                    my_project.append(lab_project.get("data", {}).get("current", {}))

                # 在任务循环中检查停止
                for task in my_project:
                    # 检查停止
                    if hasattr(self, '_adapter') and hasattr(self._adapter, '_stop_event'):
                        if self._adapter._stop_event.is_set():
                            self._adapter._log("用户中断：停止学习任务", "warning")
                            return

                    project_prefix = task["projectName"]
                    self.log.info(f"开始处理任务：{project_prefix}")
                    need_capt = []

                    self.get_progress(task["userProjectId"], project_prefix)

                    for choose_type in [(3, "必修课", "requiredNum", "requiredFinishedNum"), (1, "推送课", "pushNum", "pushFinishedNum"), (2, "自选课", "optionalNum", "optionalFinishedNum")]:
                        categories = self.api.list_category(task["userProjectId"], choose_type[0])
                        if categories.get("code") != "0":
                            self.log.error(f"获取 {choose_type[1]} 分类失败：{categories}")
                            continue
                        for category in categories.get("data", []):
                            # 检查停止
                            if hasattr(self, '_adapter') and hasattr(self._adapter, '_stop_event'):
                                if self._adapter._stop_event.is_set():
                                    self._adapter._log("用户中断：停止分类处理", "warning")
                                    return

                            category_prefix = f"{choose_type[1]} {project_prefix}/{category['categoryName']}"
                            self.log.info(f"开始处理 {category_prefix}")
                            if not restudy_time and category["finishedNum"] >= category["totalNum"]:
                                self.log.success(f"{category_prefix} 已完成")
                                continue

                            progress = self.get_progress(task["userProjectId"], project_prefix, False)
                            if not restudy_time and progress[choose_type[3]] >= progress[choose_type[2]]:
                                self.log.info(f"{category_prefix} 已达到要求，跳过")
                                break

                            courses = self.api.list_course(task["userProjectId"], category["categoryCode"], choose_type[0])
                            for course in courses.get("data", []):
                                # 检查停止
                                if hasattr(self, '_adapter') and hasattr(self._adapter, '_stop_event'):
                                    if self._adapter._stop_event.is_set():
                                        self._adapter._log("用户中断：停止课程学习", "warning")
                                        return

                                course_prefix = f"{category_prefix}/{course['resourceName']}"
                                progress = self.get_progress(task["userProjectId"], category_prefix)
                                if not restudy_time and progress[choose_type[3]] >= progress[choose_type[2]]:
                                    self.log.info(f"{category_prefix} 已达到要求，跳过")
                                    break

                                self.log.info(f"开始处理课程：{course_prefix}")
                                if not restudy_time and course["finished"] == 1:
                                    self.log.success(f"{course_prefix} 已完成")
                                    continue

                                self.api.study(course["resourceId"], task["userProjectId"])
                                if self.api.get_simple_config().get("data", {}).get("isControlSource") == 1:
                                    self.log.warning(f"检测到课程需网页端处理（isControlSource=1），建议前往网页版登录处理一下")

                                if "userCourseId" not in course:
                                    self.log.success(f"{course_prefix} 完成")
                                    continue

                                course_url = self.api.get_course_url(course["resourceId"], task["userProjectId"])["data"] + "&weiban=weiban"
                                from urllib.parse import parse_qs, urlparse
                                query = parse_qs(urlparse(course_url).query)
                                if query.get("csCapt", [None])[0] == "true":
                                    self.log.warning(f"课程需要验证码，暂时无法处理...")
                                    need_capt.append(course_prefix)
                                    continue

                                # 在学习等待循环中检查停止
                                sleep = 0
                                import time
                                while sleep < self.study_time:
                                    # 检查停止
                                    if hasattr(self, '_adapter') and hasattr(self._adapter, '_stop_event'):
                                        if self._adapter._stop_event.is_set():
                                            self._adapter._log("用户中断：停止课程等待", "warning")
                                            return

                                    if sleep % 60 == 0:
                                        self.log.info(f"{course_prefix} 等待 {self.study_time - sleep} 秒，模拟学习中...")
                                    time.sleep(1)
                                    sleep += 1

                                if query.get("lyra", [None])[0] == "lyra":
                                    res = self.api.finish_lyra(query.get("userActivityId", [None])[0])
                                elif query.get("weiban", [None])[0] != "weiban":
                                    res = self.api.finish_by_token(course["userCourseId"], course_type="open")
                                elif query.get("source", [None])[0] == "moon":
                                    res = self.api.finish_by_token(course["userCourseId"], course_type="moon")
                                else:
                                    token = None
                                    if query.get("csCapt", [None])[0] == "true":
                                        self.log.warning(f"课程需要验证码，暂时无法处理...")
                                        need_capt.append(course_prefix)
                                        continue
                                        res = self.api.invoke_captcha(course["userCourseId"], task["userProjectId"])
                                        if res.get("code", -1) != "0":
                                            self.log.error(f"获取验证码失败：{res}")
                                        token = res.get("data", {}).get("methodToken", None)

                                    res = self.api.finish_by_token(course["userCourseId"], token)
                                    if "ok" not in res:
                                        self.log.error(f"{course_prefix} 完成失败：{res}")

                                self.log.success(f"{course_prefix} 完成")

                    if need_capt:
                        self.log.warning(f"以下课程需要验证码，请手动完成：")
                        for c in need_capt:
                            self.log.warning(f" - {c}")

                    self.log.success(f"{project_prefix} 课程学习完成")

            def run_exam_with_stop(self, use_time: int = 250):
                """带停止检查的 run_exam 方法"""
                import json
                import time

                # 检查停止标志
                if hasattr(self, '_adapter') and hasattr(self._adapter, '_stop_event'):
                    if self._adapter._stop_event.is_set():
                        self._adapter._log("用户中断：考试阶段", "warning")
                        return

                # 加载题库
                answers_json = {}
                from pathlib import Path
                answer_dir = Path(__file__).parent / "WeBan" / "answer"
                answer_path = answer_dir / "answer.json"

                with open(answer_path, encoding="utf-8") as f:
                    for title, options in json.load(f).items():
                        title = WeBanClient.clean_text(title)
                        if title not in answers_json:
                            answers_json[title] = []
                        answers_json[title].extend([WeBanClient.clean_text(a["content"]) for a in options.get("optionList", []) if a["isCorrect"] == 1])

                # 获取项目
                projects = self.api.list_my_project()
                if projects.get("code", -1) != "0":
                    self.log.error(f"获取考试列表失败：{projects}")
                    return

                projects = projects.get("data", [])

                completion = self.api.list_completion()
                if completion.get("code", -1) != "0":
                    self.log.error(f"获取模块完成情况失败：{completion}")

                showable_modules = [d["module"] for d in completion.get("data", []) if d["showable"] == 1]
                if "labProject" in showable_modules:
                    self.log.info(f"加载实验室课程")
                    lab_project = self.api.lab_index()
                    if lab_project.get("code", -1) != "0":
                        self.log.error(f"获取实验室课程失败：{lab_project}")
                    projects.append(lab_project.get("data", {}).get("current", {}))

                for project in projects:
                    # 检查停止
                    if hasattr(self, '_adapter') and hasattr(self._adapter, '_stop_event'):
                        if self._adapter._stop_event.is_set():
                            self._adapter._log("用户中断：停止考试项目", "warning")
                            return

                    self.log.info(f"开始考试项目 {project['projectName']}")
                    user_project_id = project["userProjectId"]

                    # 获取考试计划
                    exam_plans = self.api.exam_list_plan(user_project_id)
                    if exam_plans.get("code", -1) != "0":
                        self.log.error(f"获取考试计划失败：{exam_plans}")
                        return
                    exam_plans = exam_plans["data"]

                    for plan in exam_plans:
                        # 检查停止
                        if hasattr(self, '_adapter') and hasattr(self._adapter, '_stop_event'):
                            if self._adapter._stop_event.is_set():
                                self._adapter._log("用户中断：停止考试计划", "warning")
                                return

                        if plan["examFinishNum"] != 0:
                            # 使用回调获取重考选择（支持 GUI）
                            if hasattr(self, '_adapter') and hasattr(self._adapter, 'input_callback'):
                                choice = self._adapter.input_callback(
                                    f"考试项目 {project['projectName']}/{plan['examPlanName']} 最高成绩 {plan['examScore']} 分。已考试次数 {plan['examFinishNum']} 次，还剩 {plan['examOddNum']} 次。需要重考吗(y/N)？"
                                ).strip().lower()
                            else:
                                with self._stdin_lock:
                                    self.log.success(f"考试项目 {project['projectName']}/{plan['examPlanName']} 最高成绩 {plan['examScore']} 分。已考试次数 {plan['examFinishNum']} 次，还剩 {plan['examOddNum']} 次。需要重考吗(y/N)？")
                                    choice = input().strip().lower()

                            if choice != "y":
                                self.log.info(f"不重考项目 {project['projectName']}")
                                continue

                        user_exam_plan_id = plan["id"]
                        exam_plan_id = plan["examPlanId"]

                        # 预请求
                        prepare_paper = self.api.exam_prepare_paper(user_exam_plan_id)
                        if prepare_paper.get("code", -1) != "0":
                            self.log.error(f"获取考试信息失败：{prepare_paper}")
                            continue
                        prepare_paper = prepare_paper["data"]
                        question_num = prepare_paper["questionNum"]
                        self.log.info(f"考试信息：用户：{prepare_paper['realName']}，ID：{prepare_paper['userIDLabel']}，题目数：{question_num}，试卷总分：{prepare_paper['paperScore']}，限时 {prepare_paper['answerTime']} 分钟")
                        per_time = use_time // prepare_paper["questionNum"]

                        # 获取考试题目
                        exam_paper = self.api.exam_start_paper(user_exam_plan_id)
                        if exam_paper.get("code", -1) != "0":
                            self.log.error(f"获取考试题目失败：{exam_paper}")
                            if exam_paper.get("detailCode") == "10018":
                                self.log.warning(f"考试项目 {project['projectName']}/{plan['examPlanName']} 需要手动处理，请在网站上开启一次考试后重试")
                            continue
                        exam_paper = exam_paper.get("data", {})
                        question_list = exam_paper.get("questionList", [])
                        have_answer = []  # 有答案的题目
                        no_answer = []  # 无答案的题目

                        for question in question_list:
                            if WeBanClient.clean_text(question["title"]) in answers_json:
                                have_answer.append(question)
                            else:
                                no_answer.append(question)

                        self.log.info(f"题目总数：{question_num}，有答案的题目数：{len(have_answer)}，无答案的题目数：{len(no_answer)}")

                        # 处理无答案的题目（需要手动输入）
                        for i, question in enumerate(no_answer):
                            # 检查停止
                            if hasattr(self, '_adapter') and hasattr(self._adapter, '_stop_event'):
                                if self._adapter._stop_event.is_set():
                                    self._adapter._log("用户中断：停止手动答题", "warning")
                                    return

                            self.log.info(f"[{i}/{len(no_answer)}]题目不在题库中或选项不同，请手动选择答案")
                            print(f"题目类型：{question['typeLabel']}，题目标题：{question['title']}")
                            for j, opt in enumerate(question["optionList"]):
                                print(f"{j + 1}. {opt['content']}")

                            opt_count = len(question["optionList"])
                            start_time = time.time()
                            answers_ids = []

                            while not answers_ids:
                                # 使用回调获取答案输入（支持 GUI）
                                if hasattr(self, '_adapter') and hasattr(self._adapter, 'input_callback'):
                                    # 构建完整的题目信息（包括选项）以便用户复制
                                    prompt_lines = [
                                        f"[{i}/{len(no_answer)}]题目不在题库中或选项不同，请手动选择答案",
                                        f"题目类型：{question['typeLabel']}，题目标题：{question['title']}",
                                    ]
                                    # 添加选项列表
                                    for j, opt in enumerate(question["optionList"]):
                                        prompt_lines.append(f"{j + 1}. {opt['content']}")
                                    # 添加输入提示
                                    prompt_lines.append("\n请输入答案序号（多个选项用英文逗号分隔，如 1,2,3,4）：")

                                    # 合并为完整的提示文本
                                    full_prompt = "\n".join(prompt_lines)

                                    answer = self._adapter.input_callback(full_prompt).replace(" ", "").replace("，", ",")
                                else:
                                    with self._stdin_lock:
                                        answer = input(f"[{self.api.user.get('realName', '未知')}] 请输入答案序号（多个选项用英文逗号分隔，如 1,2,3,4）：").replace(" ", "").replace("，", ",")

                                candidates = [ans.strip() for ans in answer.split(",") if ans.strip()]
                                if all(ans.isdigit() and 1 <= int(ans) <= opt_count for ans in candidates):
                                    answers_ids = [question["optionList"][int(ans) - 1]["id"] for ans in candidates]
                                    for ans in candidates:
                                        self.log.info(f"选择答案：{ans}，内容：{question['optionList'][int(ans)-1]['content']}")
                                else:
                                    self.log.error("输入无效，请重新输入（序号需为数字且在选项范围内）")

                            self.log.info(f"正在提交当前答案")
                            end_time = time.time()
                            if not self.record_answer(user_exam_plan_id, question["id"], round(end_time - start_time), answers_ids, exam_plan_id):
                                raise RuntimeError(f"答题失败，请重新考试：{question}")

                        self.log.info(f"手动答题结束，开始答题库中的题目，共 {len(have_answer)} 道题目")
                        for i, question in enumerate(have_answer):
                            # 检查停止
                            if hasattr(self, '_adapter') and hasattr(self._adapter, '_stop_event'):
                                if self._adapter._stop_event.is_set():
                                    self._adapter._log("用户中断：停止自动答题", "warning")
                                    return

                            self.log.info(f"[{i}/{len(have_answer)}]题目在题库中，开始答题")
                            self.log.info(f"题目类型：{question['typeLabel']}，题目标题：{question['title']}")
                            answers = answers_json[WeBanClient.clean_text(question["title"])]
                            answers_ids = [option["id"] for option in question["optionList"] if WeBanClient.clean_text(option["content"]) in answers]
                            self.log.info(f"等待 {per_time} 秒，模拟答题中...")

                            # 在等待期间也检查停止
                            sleep_count = 0
                            while sleep_count < per_time:
                                if hasattr(self, '_adapter') and hasattr(self._adapter, '_stop_event'):
                                    if self._adapter._stop_event.is_set():
                                        self._adapter._log("用户中断：停止答题等待", "warning")
                                        return
                                time.sleep(1)
                                sleep_count += 1

                            if not self.record_answer(user_exam_plan_id, question["id"], per_time + 1, answers_ids, exam_plan_id):
                                raise RuntimeError(f"答题失败，请重新考试：{question}")

                        self.log.info(f"完成考试，正在提交试卷...")
                        submit_res = self.api.exam_submit_paper(user_exam_plan_id)
                        if submit_res.get("code", -1) != "0":
                            raise RuntimeError(f"提交试卷失败，请重新考试：{submit_res}")
                        self.log.success(f"试卷提交成功，考试完成，成绩：{submit_res['data']['score']} 分")

            # 替换方法
            WeBanClient.run_study = run_study_with_stop
            WeBanClient.run_exam = run_exam_with_stop

            # 标记已应用
            WeBanClient._weban_patch_applied = True

    def _apply_input_patch(self):
        """
        应用 Monkey Patch 添加 GUI 输入支持

        将 WeBan 模块中的 input() 调用替换为回调函数
        """
        if not WEBAN_AVAILABLE:
            return

        # 使用类级别标志确保 Monkey Patch 只应用一次
        if not hasattr(WeBanClient, '_weban_input_patch_applied'):
            def login_with_gui_input(self) -> Dict | None:
                """支持 GUI 输入的登录方法"""
                if self.api.user.get("userId"):
                    return self.api.user
                retry_limit = 3
                for i in range(retry_limit + 2):
                    if i > 0:
                        self.log.warning(f"登录失败，正在重试 {i}/{retry_limit+2} 次")
                    verify_time = self.api.get_timestamp(13, 0)
                    verify_image = self.api.rand_letter_image(verify_time)
                    if i < retry_limit and self.ocr:
                        try:
                            verify_code = self.ocr.classification(verify_image)
                            self.log.info(f"自动验证码识别结果: {verify_code}")
                            if len(verify_code) != 4:
                                self.log.warning(f"验证码识别失败，正在重试")
                                continue
                        except Exception as e:
                            self.log.error(f"验证码识别异常: {e}")
                            continue
                    else:
                        import time
                        import threading
                        account_id = self.api.account or self.api.user.get("userId") or "unknown"
                        # 添加时间戳和线程ID，避免多账号同时运行时的文件覆盖
                        timestamp = int(time.time() * 1000)
                        thread_id = threading.get_ident()
                        captcha_filename = f"verify_code_{account_id}_{timestamp}_{thread_id}.png"
                        captcha_path = os.path.abspath(captcha_filename)
                        with self._stdin_lock:
                            open(captcha_path, "wb").write(verify_image)
                            webbrowser.open(f"file://{captcha_path}")

                            # 使用回调函数获取输入（支持 GUI）
                            if hasattr(self, '_adapter') and hasattr(self._adapter, 'input_callback'):
                                verify_code = self._adapter.input_callback(
                                    f"请查看 {captcha_filename} 输入验证码："
                                )
                            else:
                                verify_code = input(f"[{account_id}] 请查看 {captcha_filename} 输入验证码：")

                        # 尝试删除临时验证码图片
                        try:
                            os.remove(captcha_path)
                        except Exception:
                            pass

                    res = self.api.login(verify_code, int(verify_time))
                    if res.get("detailCode") == "67":
                        self.log.warning(f"验证码识别失败，正在重试")
                        continue
                    if self.api.user.get("userId"):
                        return self.api.user
                    self.log.error(f"登录出错，请检查 config.json 内账号密码，或删除文件后重试: {res}")
                    break
                return None

            # 替换方法
            WeBanClient.login = login_with_gui_input

            # 标记已应用
            WeBanClient._weban_input_patch_applied = True

    def load_config(self, config: List[Dict[str, Any]]) -> bool:
        """
        加载配置

        Args:
            config: WeBan 配置列表，格式参考 WeBan 的 config.json

        Returns:
            是否加载成功
        """
        if not config:
            self._log("配置为空", "error")
            return False

        # 验证配置格式
        required_fields = ["tenant_name"]
        for i, account_config in enumerate(config):
            for field in required_fields:
                if field not in account_config:
                    self._log(f"账号 {i+1} 缺少必要字段: {field}", "error")
                    return False

            # 检查是否有有效的登录信息
            has_password = all([
                account_config.get("account"),
                account_config.get("password"),
            ])
            has_token = all([
                account_config.get("user", {}).get("userId"),
                account_config.get("user", {}).get("token"),
            ])

            if not (has_password or has_token):
                self._log(f"账号 {i+1} 缺少登录信息（账号密码或 Token）", "error")
                return False

        self._config = config
        self._log(f"已加载 {len(config)} 个账号配置", "success")
        return True

    def validate_tenant(self, tenant_name: str) -> Dict[str, Any]:
        """
        验证学校名称

        Args:
            tenant_name: 学校名称

        Returns:
            验证结果，格式: {"success": bool, "message": str, "data": dict}
        """
        if not WEBAN_AVAILABLE:
            return {
                "success": False,
                "message": "WeBan 模块不可用，请检查依赖是否安装",
                "data": {}
            }

        try:
            client = WeBanClient(tenant_name=tenant_name, log=self)
            # WeBanClient 在初始化时会自动获取学校代码
            # 如果成功，tenant_code 会被设置
            if client.tenant_code:
                return {
                    "success": True,
                    "message": f"学校验证成功: {tenant_name} ({client.tenant_code})",
                    "data": {"tenant_code": client.tenant_code}
                }
            else:
                return {
                    "success": False,
                    "message": f"未找到学校: {tenant_name}",
                    "data": {}
                }
        except Exception as e:
            return {
                "success": False,
                "message": f"验证失败: {str(e)}",
                "data": {}
            }

    def run_account(self, config: Dict[str, Any], account_index: int) -> bool:
        """
        运行单个账号的任务

        Args:
            config: 账号配置
            account_index: 账号索引

        Returns:
            是否执行成功
        """
        if self._stop_event.is_set():
            self._log(f"账号 {account_index+1}: 用户中断", "warning")
            return False

        if not WEBAN_AVAILABLE:
            self._log("WeBan 模块不可用", "error")
            return False

        tenant_name = config.get("tenant_name", "").strip()
        account = config.get("account", "").strip()
        password = config.get("password", "").strip()
        user = config.get("user", {})
        study = config.get("study", True)
        study_time = int(config.get("study_time", 20))
        restudy_time = int(config.get("restudy_time", 0))
        exam = config.get("exam", True)
        exam_use_time = int(config.get("exam_use_time", 250))

        if user.get("tenantName"):
            tenant_name = user["tenantName"]

        try:
            self._log(f"[账号 {account_index+1}] 开始执行", "info")

            if all([tenant_name, user.get("userId"), user.get("token")]):
                self._log(f"[账号 {account_index+1}] 使用 Token 登录", "info")
                client = WeBanClient(tenant_name, user=user, log=self)
            elif all([tenant_name, account, password]):
                self._log(f"[账号 {account_index+1}] 使用密码登录", "info")
                client = WeBanClient(tenant_name, account, password, log=self)
            else:
                self._log(f"[账号 {account_index+1}] 缺少必要的配置信息", "error")
                return False

            # 绑定 adapter 到 client，用于停止检查
            client._adapter = self

            # 登录前检查停止标志
            if self._stop_event.is_set():
                self._log(f"[账号 {account_index+1}]: 用户中断", "warning")
                return False

            if not client.login():
                self._log(f"[账号 {account_index+1}] 登录失败", "error")
                return False

            self._log(f"[账号 {account_index+1}] 登录成功，开始同步答案", "info")

            # 同步答案前检查停止标志
            if self._stop_event.is_set():
                self._log(f"[账号 {account_index+1}]: 用户中断", "warning")
                return False
            client.sync_answers()

            if study:
                # 学习前检查停止标志
                if self._stop_event.is_set():
                    self._log(f"[账号 {account_index+1}]: 用户中断", "warning")
                    return False
                self._log(f"[账号 {account_index+1}] 开始学习 (每个任务时长: {study_time}秒)", "info")
                client.run_study(study_time, restudy_time)

            if exam:
                # 考试前检查停止标志
                if self._stop_event.is_set():
                    self._log(f"[账号 {account_index+1}]: 用户中断", "warning")
                    return False
                self._log(f"[账号 {account_index+1}] 开始考试 (总时长: {exam_use_time}秒)", "info")
                client.run_exam(exam_use_time)

            # 最终同步前检查停止标志
            if self._stop_event.is_set():
                self._log(f"[账号 {account_index+1}]: 用户中断", "warning")
                return False
            self._log(f"[账号 {account_index+1}] 最终同步答案", "info")
            client.sync_answers()

            self._log(f"[账号 {account_index+1}] 执行完成", "success")
            return True

        except PermissionError as e:
            self._log(f"[账号 {account_index+1}] 权限错误: {e}", "error")
            self._log(f"💡 提示：请检查文件权限，或以管理员身份运行", "info")
            return False
        except RuntimeError as e:
            self._log(f"[账号 {account_index+1}] 运行时错误: {e}", "error")
            # 判断是否是用户主动停止
            if "用户中断" in str(e) or self._stop_event.is_set():
                self._log(f"[账号 {account_index+1}] 用户主动停止任务", "warning")
            return False
        except ValueError as e:
            self._log(f"[账号 {account_index+1}] 参数错误: {e}", "error")
            self._log(f"💡 提示：请检查配置参数是否正确", "info")
            return False
        except ConnectionError as e:
            self._log(f"[账号 {account_index+1}] 网络连接错误: {e}", "error")
            self._log(f"💡 提示：请检查网络连接", "info")
            return False
        except TimeoutError as e:
            self._log(f"[账号 {account_index+1}] 请求超时: {e}", "error")
            self._log(f"💡 提示：网络响应过慢，请稍后重试", "info")
            return False
        except KeyboardInterrupt:
            self._log(f"[账号 {account_index+1}] 用户中断执行", "warning")
            raise
        except Exception as e:
            self._log(f"[账号 {account_index+1}] 未知错误: {type(e).__name__}: {e}", "error")
            import traceback
            self._log(f"错误详情: {traceback.format_exc()}", "error")
            return False

    def start(self, use_multithread: bool = True) -> Dict[str, int]:
        """
        开始执行所有账号任务

        Args:
            use_multithread: 是否使用多线程（仅在有多个账号时生效）

        Returns:
            执行结果统计，格式: {"success": int, "failed": int}
        """
        if not self._config:
            self._log("没有可执行的账号配置", "error")
            return {"success": 0, "failed": 0}

        self.is_running = True
        self._stop_event.clear()

        self._log(f"开始执行，共 {len(self._config)} 个账号", "info")

        success_count = 0
        failed_count = 0

        if use_multithread and len(self._config) > 1:
            # 多线程执行
            from concurrent.futures import as_completed, ThreadPoolExecutor

            max_workers = min(len(self._config), 5)  # 限制最大线程数为5
            self._log(f"使用多线程模式，最大并发数: {max_workers}", "info")

            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_account = {
                    executor.submit(self.run_account, config, i): (config, i)
                    for i, config in enumerate(self._config)
                }

                for future in as_completed(future_to_account):
                    config, account_index = future_to_account[future]
                    try:
                        success = future.result()
                        if success:
                            success_count += 1
                        else:
                            failed_count += 1
                    except Exception as e:
                        self._log(f"[账号 {account_index+1}] 线程执行异常: {e}", "error")
                        failed_count += 1

        else:
            # 单线程执行
            self._log("使用单线程模式，逐个执行", "info")
            for i, config in enumerate(self._config):
                if self._stop_event.is_set():
                    break
                success = self.run_account(config, i)
                if success:
                    success_count += 1
                else:
                    failed_count += 1

        self.is_running = False
        self._log(f"所有账号执行完成！成功: {success_count}，失败: {failed_count}",
                  "success" if failed_count == 0 else "warning")

        return {"success": success_count, "failed": failed_count}

    def stop(self):
        """优雅停止执行"""
        if self.is_running:
            self._log("正在停止执行...", "warning")
            self._stop_event.set()
            self.is_running = False

    def force_stop(self):
        """强行停止执行"""
        self._log("⚠️ 正在强行停止...", "warning")

        # 设置停止标志
        self._stop_event.set()
        self.is_running = False

        # 尝试清理资源
        try:
            # 如果有终端进程，尝试关闭
            if hasattr(self, '_terminal_process') and self._terminal_process:
                try:
                    if hasattr(self._terminal_process, 'kill'):
                        self._terminal_process.kill()
                    self._log("✅ 已关闭终端进程", "success")
                except Exception as e:
                    self._log(f"⚠️ 关闭终端失败: {e}", "warning")
        except Exception as e:
            self._log(f"⚠️ 强行停止时出错: {e}", "error")

        self._log("✅ 已强行停止任务", "success")

    def start_in_terminal(self) -> bool:
        """
        在独立终端窗口中运行 WeBan

        这个方法会打开一个新的终端窗口，在其中运行 WeBan 模块。
        所有用户交互（验证码输入、手动答题等）都在新终端中进行。

        Returns:
            是否成功启动
        """
        if not self._config:
            self._log("没有可执行的账号配置", "error")
            return False

        try:
            # 从同一目录导入 WeBanRunner
            import importlib.util
            runner_path = Path(__file__).parent / "weban_runner.py"
            spec = importlib.util.spec_from_file_location("weban_runner", runner_path)
            weban_runner = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(weban_runner)
            WeBanRunner = weban_runner.WeBanRunner

            runner = WeBanRunner()

            self._log(f"正在启动 WeBan 独立终端...", "info")
            self._log(f"配置账号数: {len(self._config)}", "info")

            # 在独立终端中运行
            process = runner.run_in_terminal(self._config)

            self._log("✅ WeBan 独立终端已启动", "success")
            self._log("💡 所有交互（验证码、答题等）请在新终端窗口中进行", "info")

            self.is_running = True
            self._terminal_process = process
            return True

        except Exception as e:
            self._log(f"❌ 启动独立终端失败: {e}", "error")
            import traceback
            traceback.print_exc()
            return False

    # 实现 loguru logger 的接口，使 WeBanClient 可以使用
    def info(self, msg: str, *args, **kwargs):
        """info 日志"""
        self._log(msg, "info")

    def success(self, msg: str, *args, **kwargs):
        """success 日志"""
        self._log(msg, "success")

    def warning(self, msg: str, *args, **kwargs):
        """warning 日志"""
        self._log(msg, "warning")

    def error(self, msg: str, *args, **kwargs):
        """error 日志"""
        self._log(msg, "error")

    def debug(self, msg: str, *args, **kwargs):
        """debug 日志"""
        # 不显示 debug 日志
        pass

    def bind(self, **kwargs):
        """bind 方法（用于 loguru 的 extra 参数）"""
        return self

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


def get_weban_adapter(
    progress_callback: Optional[Callable[[str, str], None]] = None,
    input_callback: Optional[Callable[[str], str]] = None
) -> WeBanAdapter:
    """
    获取 WeBan 适配器实例

    Args:
        progress_callback: 进度回调函数
        input_callback: 用户输入回调函数

    Returns:
        WeBanAdapter 实例
    """
    return WeBanAdapter(
        progress_callback=progress_callback,
        input_callback=input_callback
    )

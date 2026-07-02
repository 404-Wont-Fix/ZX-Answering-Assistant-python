使用两个 skill 做完了只读深度 review，没有改任何文件，工作区仍是干净的。

**ArchAirlock**
`decision`: `ROUTE`  
`risk_level`: `HIGH`  
`primary_route`: `maintenance-guardian`  
`secondary_routes`: `architecture-discovery`, 后续若修复插件/启动边界则需要 `architecture-guardian`  
`blocked_reason`: 空，本轮是只读审查，不进入实现  
`verification_required`: 多课程导入导出回归、云考试监听回归、插件启动副作用回归、现有 unittest

**主要问题**

1. **[必须修复] 多课程题库导出/导入链路会断，且可能丢数据或直接崩溃**  
   [exporter.py](/Users/aiden/Documents/ZX-Answering-Assistant-python/src/extraction/exporter.py:230) 导出顶层字段是 `courses`，但 [importer.py](/Users/aiden/Documents/ZX-Answering-Assistant-python/src/extraction/importer.py:52) 只识别 `course_list`，[importer.py](/Users/aiden/Documents/ZX-Answering-Assistant-python/src/extraction/importer.py:117) 也只从 `course_list` 读。  
   另外 [exporter.py](/Users/aiden/Documents/ZX-Answering-Assistant-python/src/extraction/exporter.py:319) 和 [exporter.py](/Users/aiden/Documents/ZX-Answering-Assistant-python/src/extraction/exporter.py:321) 缩进导致只保留最后一个知识点；无题知识点会触发 `UnboundLocalError`。我用无写入 stub 复现了：2 个知识点只导出 1 个，空知识点直接异常。  
   建议先统一 schema，再补导出/导入闭环测试。

2. **[必须修复] 云考试 API 监听默认捕获不到请求**  
   [workflow.py](/Users/aiden/Documents/ZX-Answering-Assistant-python/src/cloud_exam/workflow.py:27) 默认 pattern 是 `*GetQuestionsByExpId*`，但 [workflow.py](/Users/aiden/Documents/ZX-Answering-Assistant-python/src/cloud_exam/workflow.py:58) 和 [workflow.py](/Users/aiden/Documents/ZX-Answering-Assistant-python/src/cloud_exam/workflow.py:70) 用的是普通 `in` 判断。实际 URL 不包含星号，所以监听基本失效。  
   建议改成 `fnmatch`/Playwright glob，或默认值直接用 `GetQuestionsByExpId`。

3. **[必须修复] 主启动链路导入可选 WeBan 插件，产生隐藏副作用**  
   [version.py](/Users/aiden/Documents/ZX-Answering-Assistant-python/version.py:72) 为了取 WeBan 版本导入插件 `main.py`；插件初始化又在 [__init__.py](/Users/aiden/Documents/ZX-Answering-Assistant-python/plugins/weban_plugin/__init__.py:31) 修改全局 `sys.path`，并在 [main.py](/Users/aiden/Documents/ZX-Answering-Assistant-python/plugins/weban_plugin/modules/WeBan/main.py:35) 重配 loguru、在 [main.py](/Users/aiden/Documents/ZX-Answering-Assistant-python/plugins/weban_plugin/modules/WeBan/main.py:45) 创建日志目录。  
   建议版本读取改为静态文本/AST/metadata，不 import 插件运行入口。

4. **[必须修复] WeBan 插件依赖声明不完整**  
   WeBan 代码直接依赖 [pyaes](/Users/aiden/Documents/ZX-Answering-Assistant-python/plugins/weban_plugin/modules/WeBan/api.py:10)、[nodriver/cv2/numpy](/Users/aiden/Documents/ZX-Answering-Assistant-python/plugins/weban_plugin/modules/WeBan/captcha.py:28)，但外层 [requirements.txt](/Users/aiden/Documents/ZX-Answering-Assistant-python/plugins/weban_plugin/requirements.txt:17) 没声明 `pyaes`、`nodriver`、`opencv-python-headless`。CI 也只安装外层插件 requirements。  
   建议合并或显式安装 `modules/WeBan/requirements.txt`，并让 PluginManager 校验版本约束。

5. **[建议修改] 凭据明文持久化风险偏高**  
   学生、教师、WeBan 密码分别写入 [config.py](/Users/aiden/Documents/ZX-Answering-Assistant-python/src/core/config.py:222)、[config.py](/Users/aiden/Documents/ZX-Answering-Assistant-python/src/core/config.py:271)、[config.py](/Users/aiden/Documents/ZX-Answering-Assistant-python/src/core/config.py:323)。`chmod(0600)` 有帮助，但 Windows/macOS 桌面应用更适合接 OS keychain/keyring，配置文件只存引用或非敏感偏好。

6. **[建议修改] 可维护性压力已经很高**  
   AST 扫描显示 71 个 Python 文件无语法错误，但有多个超大类/函数：`AnsweringView` 2773 行、`AutoAnswer` 1719 行、`Extractor` 1326 行，最长函数 `navigate_to_course_page` 617 行。现有测试只有 10 个，覆盖不到 GUI、浏览器、题库闭环、云考试、插件运行。建议先围绕上面 4 个必须修复点补小型回归测试，再拆函数。

7. **[仅供参考] 版本元数据不一致**  
   [version.py](/Users/aiden/Documents/ZX-Answering-Assistant-python/version.py:62) 和 README 是 `3.7.4`，但 [pyproject.toml](/Users/aiden/Documents/ZX-Answering-Assistant-python/pyproject.toml:3) 是 `3.7.2`。发布和用户排障时容易混淆。

**验证记录**

- `git status --short`: 无输出，未改动工作区  
- `.venv/bin/python -B -m unittest discover -s tests -v`: 10 个测试全部通过  
- AST 语法检查：71 个 Python 文件，0 个语法错误  
- 额外复现：多课程导出会只保留 1 个知识点，空知识点触发 `UnboundLocalError`，云考试 pattern 字面匹配为 `False`

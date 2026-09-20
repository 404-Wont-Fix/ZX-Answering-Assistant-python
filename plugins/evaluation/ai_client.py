"""
AI 与检索客户端 - OpenAI-compatible JSON client and optional HTTP MCP search adapter.

两条独立通道：

1. :class:`StructuredAIClient` —— OpenAI 兼容 ``/chat/completions``，强制 JSON 输出，
   解析失败自动重试；**不做** 0 配置免 key 兜底（AI Key 必须由用户在插件设置里提供）。
2. :class:`HttpMcpSearchClient` —— Exa 托管 MCP（默认 ``https://mcp.exa.ai/mcp``）。
   优先**免 key** 使用（IP 限额）；额度不足时用用户提供的 ``exa_api_key``；
   两者都失败则返回空结果，调用方降级为「模型自有知识出题」。

⚠️ 该模块不导入 flet / docx，保证 ``plugins/evaluation/ui.py`` 在缺依赖时仍可导入。
"""

from __future__ import annotations

import json
from typing import Any, Callable

import requests

# ---------------------------------------------------------------- 常量
DEFAULT_BASE_URL = "https://api.deepseek.com/v1"
DEFAULT_MODEL = "deepseek-chat"
DEFAULT_EXA_MCP_URL = "https://mcp.exa.ai/mcp"

# Exa MCP 工具名
EXA_SEARCH_TOOL = "web_search_exa"

_ACCEPT_HEADER = "application/json, text/event-stream"


class AIConfigError(RuntimeError):
    """AI 配置缺失（用于 UI 层引导用户打开插件设置）。"""


# ------------------------------------------------------------------ 字段别名
# 实测：即使提示词写了字段契约，模型仍可能自创别名（deepseek-v4-flash 曾把题干
# 放在 ``question``）。这里做容错，**并且记录告警**，避免静默丢掉题干。
FIELD_ALIASES: dict[str, tuple[str, ...]] = {
    "stem": ("stem", "question", "question_stem", "title", "content", "题干", "题目"),
    "type": ("type", "question_type", "questionType", "题型", "qtype"),
    "difficulty": ("difficulty", "level", "难度", "difficulty_level"),
    "options": ("options", "choices", "option_list", "optionList", "选项"),
    "answer": ("answer", "correct_answer", "correctAnswer", "answers", "correct", "答案"),
    "confidence": ("confidence", "score", "conf", "confidence_score", "置信度"),
    "rationale": ("rationale", "reason", "explanation", "analysis", "解析", "说明"),
}


def pick_field(raw: dict, field: str, default=None):
    """
    从模型返回项里按「标准名 → 别名」顺序取值。

    Returns:
        (值, 实际命中的键名)；未命中返回 (default, None)
    """
    if not isinstance(raw, dict):
        return default, None

    for key in FIELD_ALIASES.get(field, (field,)):
        if key in raw and raw[key] not in (None, "", []):
            return raw[key], key
    return default, None


class StructuredAIClient:
    """
    OpenAI 兼容的 JSON 出题客户端。

    Args:
        config: 插件配置 dict，需含 ``api_key`` / ``base_url`` / ``model``
        session: 可注入的 ``requests.Session``（便于单测）
        logger: 可选日志回调
    """

    def __init__(
        self,
        config: dict[str, Any],
        session: requests.Session | None = None,
        logger: Callable[[str], None] | None = None,
    ) -> None:
        self.config = dict(config or {})
        self.session = session or requests.Session()
        self._log = logger or (lambda message: None)

    # ------------------------------------------------------------ 配置
    @property
    def api_key(self) -> str:
        return str(self.config.get("api_key") or "").strip()

    @property
    def base_url(self) -> str:
        return str(self.config.get("base_url") or DEFAULT_BASE_URL).strip()

    @property
    def model(self) -> str:
        return str(self.config.get("model") or DEFAULT_MODEL).strip()

    def ensure_configured(self) -> None:
        """配置缺失时抛 :class:`AIConfigError`（UI 层据此引导打开设置）。"""
        if not self.api_key:
            raise AIConfigError("未配置 AI API Key")
        if not self.base_url:
            raise AIConfigError("未配置 AI Base URL")

    # ------------------------------------------------------------ 调用
    def test_connection(self, *, timeout: tuple[int, int] = (10, 30)) -> dict[str, Any]:
        """调用同一模型接口验证配置、网络和 OpenAI 兼容响应。"""
        return self.complete_json(
            system="你是连接测试助手。",
            user='只返回严格 JSON：{"ok": true}',
            retries=0,
            timeout=timeout,
            temperature=0,
            validate=lambda payload: isinstance(payload, dict),
            invalid_reason="连接测试返回不是 JSON 对象",
        )

    def generate(
        self,
        request_payload: dict[str, Any],
        *,
        retries: int = 2,
        timeout: tuple[int, int] = (10, 180),
        temperature: float = 0.6,
    ) -> dict[str, Any]:
        """
        发起一次出题请求，返回 ``{"questions": [...]}``。

        Args:
            request_payload: :func:`plugins.evaluation.prompts.build_generation_request` 的返回值
            retries: JSON 不合规时的重试次数
            timeout: (连接超时, 读取超时)
            temperature: 采样温度（教学题偏稳定，默认 0.6）

        Raises:
            AIConfigError: 未配置 api_key / base_url
            RuntimeError: 重试后仍拿不到合规 JSON
        """
        parsed = self.complete_json(
            system=request_payload.get("system", ""),
            user=request_payload.get("user", ""),
            retries=retries,
            timeout=timeout,
            temperature=temperature,
            validate=lambda payload: isinstance(payload, dict)
            and isinstance(payload.get("questions"), list),
            invalid_reason="AI 返回缺少 questions 数组",
        )
        return parsed

    def complete_json(
        self,
        *,
        system: str,
        user: str,
        retries: int = 2,
        timeout: tuple[int, int] = (10, 120),
        temperature: float = 0.4,
        validate: Callable[[Any], bool] | None = None,
        invalid_reason: str = "AI 返回不合规",
    ) -> Any:
        """
        通用 JSON 补全（用于［AI 建议考点］/［AI 提取候选］）。

        Args:
            validate: 可选的额外校验；返回 False 则重试
            invalid_reason: 校验失败时日志/异常里的描述
        """
        self.ensure_configured()

        url = f"{self.base_url.rstrip('/')}/chat/completions"
        body = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": temperature,
            "response_format": {"type": "json_object"},
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        last_error: Exception | None = None
        for attempt in range(max(int(retries), 0) + 1):
            try:
                response = self.session.post(
                    url, json=body, headers=headers, timeout=timeout
                )
                response.raise_for_status()
                data = response.json()
            except requests.RequestException as exc:
                last_error = exc
                self._log(f"AI 请求失败（第 {attempt + 1} 次）：{exc}")
                continue
            except (ValueError, json.JSONDecodeError) as exc:
                last_error = exc
                self._log(f"AI 响应不是合法 JSON（第 {attempt + 1} 次）：{exc}")
                continue

            try:
                content = data["choices"][0]["message"]["content"]
            except (KeyError, IndexError, TypeError) as exc:
                last_error = exc
                self._log(f"AI 响应结构异常（第 {attempt + 1} 次）：{exc}")
                continue

            parsed = parse_json_content(content)
            if parsed is None:
                last_error = ValueError(invalid_reason)
                self._log(f"{invalid_reason}（第 {attempt + 1} 次）")
                continue

            if validate is not None and not validate(parsed):
                last_error = ValueError(invalid_reason)
                self._log(f"{invalid_reason}（第 {attempt + 1} 次）")
                continue

            return parsed

        raise RuntimeError(f"AI 返回不合规，重试后仍失败: {last_error}")


class HttpMcpSearchClient:
    """
    极简 HTTP MCP 适配器（当前用于 Exa 的 ``web_search_exa``）。

    免 key 优先 → 用户 key 兜底 → 全部失败返回 ``""``（调用方降级）。
    """

    def __init__(
        self,
        config: dict[str, Any],
        session: requests.Session | None = None,
        logger: Callable[[str], None] | None = None,
    ) -> None:
        self.config = dict(config or {})
        self.session = session or requests.Session()
        self._log = logger or (lambda message: None)

    @property
    def mcp_url(self) -> str:
        return str(self.config.get("exa_mcp_url") or DEFAULT_EXA_MCP_URL).strip()

    @property
    def api_key(self) -> str:
        return str(self.config.get("exa_api_key") or "").strip()

    def search(
        self,
        query: str,
        *,
        num_results: int = 5,
        timeout: tuple[int, int] = (5, 60),
    ) -> str:
        """
        执行一次联网检索。

        Returns:
            str: 可拼进提示词的检索摘要；失败/无结果返回 ``""``（**从不抛异常**）
        """
        if not self.mcp_url or not (query or "").strip():
            return ""

        attempts: list[dict[str, str]] = []
        # 1) 免 key（IP 限额）：优先按用户回答的「0 配置模式」走
        attempts.append({"url": self.mcp_url, "auth": ""})
        # 2) 用户 key 兜底
        if self.api_key:
            separator = "&" if "?" in self.mcp_url else "?"
            attempts.append(
                {
                    "url": f"{self.mcp_url}{separator}exaApiKey={self.api_key}",
                    "auth": f"Bearer {self.api_key}",
                }
            )

        for index, attempt in enumerate(attempts):
            try:
                text = self._call(attempt["url"], attempt["auth"], query, num_results, timeout)
            except Exception as exc:  # noqa: BLE001 - 检索失败绝不能中断出题
                self._log(f"检索失败（尝试 {index + 1}/{len(attempts)}）：{exc}")
                continue

            if text:
                return text

        self._log("联网检索不可用，已降级为模型自有知识")
        return ""

    # ------------------------------------------------------------ 内部
    def _call(
        self,
        url: str,
        auth: str,
        query: str,
        num_results: int,
        timeout: tuple[int, int],
    ) -> str:
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": EXA_SEARCH_TOOL,
                "arguments": {"query": query, "numResults": int(num_results)},
            },
        }
        headers = {
            "Content-Type": "application/json",
            "Accept": _ACCEPT_HEADER,
        }
        if auth:
            headers["Authorization"] = auth

        response = self.session.post(
            url, json=payload, headers=headers, stream=True, timeout=timeout
        )
        response.raise_for_status()

        content_type = str(response.headers.get("Content-Type", "")).lower()
        if "text/event-stream" in content_type:
            data = _read_sse_messages(response)
        else:
            data = response.json()

        return _summarize_mcp_result(data)


# ---------------------------------------------------------------- 解析工具
def _read_sse_messages(response) -> dict[str, Any]:
    """
    读取 SSE 流并返回最后一条可解析的消息。

    ⚠️ SSE 场景**不能**直接调 ``response.json()``（会抛解析异常），
    必须逐行累积 ``data:`` 之后的内容。
    """
    buffer: list[str] = []
    last_message: dict[str, Any] = {}

    for raw_line in response.iter_lines(decode_unicode=True):
        line = raw_line or ""
        if not line:
            # 空行 = 一条消息结束
            if buffer:
                parsed = parse_json_content("\n".join(buffer))
                if isinstance(parsed, dict) and parsed:
                    last_message = parsed
                buffer = []
            continue

        if line.startswith("data:"):
            buffer.append(line[len("data:") :].strip())
        # 忽略 event: / id: / retry: 等 SSE 字段

    if buffer:
        parsed = parse_json_content("\n".join(buffer))
        if isinstance(parsed, dict) and parsed:
            last_message = parsed

    return last_message


def _summarize_mcp_result(data: Any) -> str:
    """把 MCP ``tools/call`` 的返回压成一段可读文本（失败返回 ""）。"""
    if not isinstance(data, dict):
        return ""

    if data.get("error"):
        raise RuntimeError(f"MCP error: {data['error']}")

    result = data.get("result")
    if not isinstance(result, dict):
        return ""

    parts: list[str] = []
    for item in result.get("content") or []:
        if not isinstance(item, dict):
            continue
        text = item.get("text")
        if not isinstance(text, str):
            continue
        parsed = parse_json_content(text)
        if parsed is not None:
            parts.append(_flatten_search_payload(parsed))
        else:
            parts.append(text)

    return "\n".join(part for part in parts if part).strip()


def _flatten_search_payload(payload: Any) -> str:
    """把 Exa 的结果 JSON（或纯文本）压成 ``标题 | 摘要`` 行。"""
    if isinstance(payload, str):
        return payload
    if isinstance(payload, dict):
        results = payload.get("results")
        if isinstance(results, list):
            lines = []
            for item in results[:5]:
                if not isinstance(item, dict):
                    continue
                title = str(item.get("title") or "").strip()
                snippet = str(
                    item.get("text") or item.get("snippet") or item.get("summary") or ""
                ).strip()
                snippet = " ".join(snippet.split())[:300]
                if title or snippet:
                    lines.append(f"- {title}：{snippet}" if title else f"- {snippet}")
            return "\n".join(lines)
    return json.dumps(payload, ensure_ascii=False)[:1500]


def parse_json_content(content: Any) -> Any:
    """
    宽容解析模型/MCP 返回的 JSON 文本。

    依次尝试：直接解析 → 去掉 ``` 围栏 → 截取首个 ``{`` 到最后一个 ``}``。
    全部失败返回 ``None``。
    """
    if isinstance(content, (dict, list)):
        return content
    if not isinstance(content, str) or not content.strip():
        return None

    text = content.strip()
    try:
        return json.loads(text)
    except (ValueError, json.JSONDecodeError):
        pass

    if text.startswith("```"):
        stripped = text.strip("`")
        if stripped.lower().startswith("json"):
            stripped = stripped[4:]
        try:
            return json.loads(stripped.strip())
        except (ValueError, json.JSONDecodeError):
            pass

    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except (ValueError, json.JSONDecodeError):
            return None

    return None


def should_search(uncertainty: bool, online_search: bool) -> bool:
    """是否需要联网检索：开关打开 **且** AI 对某考点不确定。"""
    return bool(uncertainty) and bool(online_search)

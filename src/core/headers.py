"""
浏览器指纹请求头常量

集中管理所有 API 调用使用的 HTTP 请求头，避免版本号不一致和重复代码。
各 profile 的值原样保留，不做版本变更。

使用方式：
    from src.core.headers import get_api_headers
    headers = get_api_headers("edge_143", token, referer="https://...", extra_headers={...})
"""

# ============================================================================
# Profile A: Chrome 138（无 Edge）
# 用于：学生端 API 做题、学生端课程相关请求
# ============================================================================

_CHROME_138 = {
    "accept": "application/json, text/plain, */*",
    "accept-language": "zh-CN,zh;q=0.9",
    "sec-ch-ua": '"Chromium";v="138", "Not)A;Brand";v="8"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
}

# ============================================================================
# Profile B: Edge 143
# 用于：教师端题目提取、云考试
# ============================================================================

_EDGE_143 = {
    "accept": "application/json, text/plain, */*",
    "accept-language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
    "sec-ch-ua": '"Microsoft Edge";v="143", "Chromium";v="143", "Not A(Brand";v="24"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36 Edg/143.0.0.0",
}

# ============================================================================
# Profile C: Edge 144
# 用于：课程认证
# ============================================================================

_EDGE_144 = {
    "accept": "application/json, text/plain, */*",
    "accept-language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
    "sec-ch-ua": '"Not(A:Brand";v="8", "Chromium";v="144", "Microsoft Edge";v="144"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36 Edg/144.0.0.0",
}

# Profile 查找表
_PROFILES = {
    "chrome_138": _CHROME_138,
    "edge_143": _EDGE_143,
    "edge_144": _EDGE_144,
}


def get_api_headers(
    profile: str,
    token: str,
    referer: str,
    extra_headers: dict = None,
) -> dict:
    """
    构建 API 请求头。

    Args:
        profile: 浏览器 profile 名称，可选 "chrome_138"、"edge_143"、"edge_144"
        token: access_token，自动填入 Bearer authorization
        referer: referer URL
        extra_headers: 额外的请求头字段（如 content-type、origin、dnt 等）

    Returns:
        请求头字典（副本，可安全修改）

    Raises:
        ValueError: profile 名称不存在
    """
    base = _PROFILES.get(profile)
    if base is None:
        raise ValueError(
            f"Unknown profile: {profile!r}. "
            f"Available: {', '.join(sorted(_PROFILES))}"
        )

    headers = base.copy()
    headers["authorization"] = f"Bearer {token}"
    headers["referer"] = referer

    if extra_headers:
        headers.update(extra_headers)

    return headers

"""
API请求模块
负责统一管理所有API请求，支持可配置的重试次数和请求速率
"""

import requests
import time
import logging
import hashlib
import json
import threading
from typing import Optional, Dict, Any, Callable
from src.core.config import get_settings_manager, APIRateLevel

logger = logging.getLogger(__name__)


class APIClient:
    """API客户端，负责发送HTTP请求并处理重试逻辑"""

    def __init__(self, settings_manager=None):
        """
        初始化API客户端

        Args:
            settings_manager: 设置管理器实例，如果不提供则使用全局实例
        """
        self.settings_manager = settings_manager or get_settings_manager()
        self._last_request_time = 0
        # 缓存存储: {cache_key: (data, expiry_time)}
        self._cache = {}
        self._cache_lock = threading.Lock()

    def _generate_cache_key(self, method: str, url: str, **kwargs) -> str:
        """
        生成缓存键

        Args:
            method: 请求方法
            url: 请求URL
            **kwargs: 请求参数

        Returns:
            str: 缓存键
        """
        # 创建一个包含请求详情的字符串
        cache_data = {
            'method': method.upper(),
            'url': url,
            'params': kwargs.get('params', {}),
            'json': kwargs.get('json', {}),
            'data': kwargs.get('data', {})
        }
        # 转换为JSON并哈希
        cache_str = json.dumps(cache_data, sort_keys=True)
        return hashlib.md5(cache_str.encode()).hexdigest()

    def _get_cached(self, cache_key: str) -> Optional[Any]:
        """
        从缓存获取数据

        Args:
            cache_key: 缓存键

        Returns:
            Optional[Any]: 缓存的数据，如果不存在或已过期则返回None
        """
        with self._cache_lock:
            if cache_key in self._cache:
                data, expiry_time = self._cache[cache_key]
                if time.time() < expiry_time:
                    logger.debug(f"缓存命中: {cache_key}")
                    return data
                else:
                    # 缓存已过期，删除
                    del self._cache[cache_key]
                    logger.debug(f"缓存已过期: {cache_key}")
        return None

    def _set_cached(self, cache_key: str, data: Any, ttl: int = 300):
        """
        设置缓存

        Args:
            cache_key: 缓存键
            data: 要缓存的数据
            ttl: 缓存生存时间（秒），默认5分钟
        """
        with self._cache_lock:
            expiry_time = time.time() + ttl
            self._cache[cache_key] = (data, expiry_time)
            logger.debug(f"数据已缓存: {cache_key}, TTL: {ttl}秒")

    def clear_cache(self):
        """清空所有缓存"""
        with self._cache_lock:
            self._cache.clear()
        logger.info("API缓存已清空")

    def get_cache_size(self) -> int:
        """获取缓存大小"""
        with self._cache_lock:
            return len(self._cache)

    def _apply_rate_limit(self):
        """应用速率限制"""
        rate_level = self.settings_manager.get_rate_level()
        delay_ms = rate_level.get_delay_ms()

        if delay_ms > 0:
            current_time = time.time()
            elapsed = (current_time - self._last_request_time) * 1000  # 转换为毫秒

            if elapsed < delay_ms:
                sleep_time = (delay_ms - elapsed) / 1000  # 转换为秒
                if sleep_time > 0.1:  # 只在等待时间超过100ms时显示提示
                    print(f"⏳ 限速: 距上次请求{elapsed:.0f}ms，需等待{sleep_time:.2f}s", flush=True)
                time.sleep(sleep_time)

        self._last_request_time = time.time()

    def _should_retry(self, response: Optional[requests.Response], error: Exception, attempt: int, max_retries: int) -> bool:
        """
        判断是否应该重试

        Args:
            response: 响应对象
            error: 异常对象
            attempt: 当前尝试次数
            max_retries: 最大重试次数

        Returns:
            bool: 是否应该重试
        """
        # 如果已经达到最大重试次数，不再重试
        if attempt >= max_retries - 1:
            return False

        # 检查特定错误类型
        if error:
            error_str = str(error)
            # 网络连接错误，应该重试
            is_network_error = (
                "ConnectionResetError" in error_str or
                "Connection aborted" in error_str or
                "RemoteDisconnected" in error_str or
                "远程主机" in error_str or
                "10054" in error_str or
                isinstance(error, (requests.exceptions.ConnectionError,
                                  requests.exceptions.Timeout))
            )
            return is_network_error

        # 检查响应状态码
        if response:
            # 5xx服务器错误，应该重试
            if 500 <= response.status_code < 600:
                return True
            # 429 Too Many Requests，应该重试
            if response.status_code == 429:
                return True

        return False

    def request(self,
                method: str,
                url: str,
                max_retries: Optional[int] = None,
                rate_limit: bool = True,
                use_cache: bool = False,
                cache_ttl: int = 300,
                **kwargs) -> Optional[requests.Response]:
        """
        发送HTTP请求

        Args:
            method: 请求方法 (GET, POST, PUT, DELETE等)
            url: 请求URL
            max_retries: 最大重试次数，如果不提供则从配置读取
            rate_limit: 是否应用速率限制
            use_cache: 是否使用缓存（仅对GET请求有效）
            cache_ttl: 缓存生存时间（秒），默认5分钟
            **kwargs: 其他requests.request参数

        Returns:
            Optional[requests.Response]: 响应对象，如果失败则返回None
        """
        method = method.upper()

        # 对于GET请求，检查缓存
        if use_cache and method == "GET":
            cache_key = self._generate_cache_key(method, url, **kwargs)
            cached_response = self._get_cached(cache_key)
            if cached_response is not None:
                return cached_response

        if max_retries is None:
            max_retries = self.settings_manager.get_max_retries()

        method = method.upper()
        last_error = None

        for attempt in range(max_retries):
            response = None
            error = None

            try:
                # 应用速率限制（每次请求前都应用，不仅仅是重试时）
                if rate_limit:
                    self._apply_rate_limit()

                # 发送请求
                response = requests.request(method, url, timeout=30, **kwargs)

                # 检查响应状态
                if response.status_code == 200:
                    # 对于GET请求，缓存响应
                    if use_cache and method == "GET":
                        cache_key = self._generate_cache_key(method, url, **kwargs)
                        self._set_cached(cache_key, response, cache_ttl)
                    return response

                # 判断是否需要重试
                if not self._should_retry(response, error, attempt, max_retries):
                    logger.error(f"❌ 请求失败: {method} {url}")
                    logger.error(f"   状态码: {response.status_code}")
                    logger.error(f"   响应内容: {response.text[:500]}")
                    return None

                # 需要重试
                if attempt < max_retries - 1:
                    delay = 2 ** attempt  # 指数退避: 1s, 2s, 4s...
                    logger.warning(f"⚠️ 请求失败，{delay}秒后重试... ({attempt + 1}/{max_retries})")
                    logger.warning(f"   状态码: {response.status_code}")
                    time.sleep(delay)
                else:
                    logger.error(f"❌ 请求失败，已达最大重试次数: {method} {url}")
                    logger.error(f"   状态码: {response.status_code}")
                    return None

            except requests.exceptions.RequestException as e:
                error = e
                last_error = e

                # 判断是否需要重试
                if not self._should_retry(response, error, attempt, max_retries):
                    logger.error(f"❌ 请求异常: {method} {url}")
                    logger.error(f"   错误: {str(e)}")
                    return None

                # 需要重试
                if attempt < max_retries - 1:
                    delay = 2 ** attempt  # 指数退避: 1s, 2s, 4s...
                    logger.warning(f"⚠️ 请求异常，{delay}秒后重试... ({attempt + 1}/{max_retries})")
                    logger.warning(f"   错误: {str(e)}")
                    time.sleep(delay)
                else:
                    logger.error(f"❌ 请求异常，已达最大重试次数: {method} {url}")
                    logger.error(f"   错误: {str(e)}")
                    return None

            except Exception as e:
                logger.error(f"❌ 未知异常: {method} {url}")
                logger.error(f"   错误: {str(e)}")
                return None

        return None

    def get(self, url: str, **kwargs) -> Optional[requests.Response]:
        """发送GET请求"""
        return self.request("GET", url, **kwargs)

    def post(self, url: str, **kwargs) -> Optional[requests.Response]:
        """发送POST请求"""
        return self.request("POST", url, **kwargs)

    def put(self, url: str, **kwargs) -> Optional[requests.Response]:
        """发送PUT请求"""
        return self.request("PUT", url, **kwargs)

    def delete(self, url: str, **kwargs) -> Optional[requests.Response]:
        """发送DELETE请求"""
        return self.request("DELETE", url, **kwargs)

    def get_json(self, url: str, **kwargs) -> Optional[Dict]:
        """
        发送GET请求并解析JSON响应

        Args:
            url: 请求URL
            **kwargs: 其他requests.get参数

        Returns:
            Optional[Dict]: 解析后的JSON数据，如果失败则返回None
        """
        response = self.get(url, **kwargs)
        if response and response.status_code == 200:
            try:
                return response.json()
            except Exception as e:
                logger.error(f"❌ 解析JSON响应失败: {str(e)}")
                return None
        return None

    def post_json(self, url: str, data: Dict = None, json_data: Dict = None, **kwargs) -> Optional[Dict]:
        """
        发送POST请求并解析JSON响应

        Args:
            url: 请求URL
            data: 表单数据
            json_data: JSON数据
            **kwargs: 其他requests.post参数

        Returns:
            Optional[Dict]: 解析后的JSON数据，如果失败则返回None
        """
        if json_data:
            kwargs['json'] = json_data
        if data:
            kwargs['data'] = data

        response = self.post(url, **kwargs)
        if response and response.status_code == 200:
            try:
                return response.json()
            except Exception as e:
                logger.error(f"❌ 解析JSON响应失败: {str(e)}")
                return None
        return None


# 创建全局API客户端实例
_api_client: Optional[APIClient] = None


def get_api_client() -> APIClient:
    """获取全局API客户端实例"""
    global _api_client
    if _api_client is None:
        _api_client = APIClient()
    return _api_client


def reset_api_client():
    """重置全局API客户端实例"""
    global _api_client
    _api_client = None

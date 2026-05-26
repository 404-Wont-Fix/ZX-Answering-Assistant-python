import json
import unittest
from unittest.mock import patch

import requests

from src.certification.api_answer import APICourseAnswer
from src.core.api_client import APIClient


class StubSettings:
    def get_max_retries(self):
        return 3


def make_response(status_code, payload=None):
    response = requests.Response()
    response.status_code = status_code
    response._content = json.dumps(payload or {}).encode("utf-8")
    response.encoding = "utf-8"
    return response


class APIClientTests(unittest.TestCase):
    def setUp(self):
        self.client = APIClient(settings_manager=StubSettings())

    @patch("src.core.api_client.requests.request")
    def test_accepts_success_status_and_preserves_custom_timeout(self, request):
        expected = make_response(201, {"created": True})
        request.return_value = expected

        response = self.client.post(
            "https://example.test/items",
            timeout=5,
            rate_limit=False,
        )

        self.assertIs(response, expected)
        request.assert_called_once_with("POST", "https://example.test/items", timeout=5)

    @patch("src.core.api_client.time.sleep")
    @patch("src.core.api_client.requests.request")
    def test_retries_retryable_http_status(self, request, sleep):
        expected = make_response(200, {"ok": True})
        request.side_effect = [make_response(503), expected]

        response = self.client.get(
            "https://example.test/items",
            max_retries=2,
            rate_limit=False,
        )

        self.assertIs(response, expected)
        self.assertEqual(request.call_count, 2)
        sleep.assert_called_once_with(1)

    @patch("src.core.api_client.requests.request")
    def test_zero_configured_attempts_still_sends_one_request(self, request):
        expected = make_response(200)
        request.return_value = expected

        response = self.client.get(
            "https://example.test/items",
            max_retries=0,
            rate_limit=False,
        )

        self.assertIs(response, expected)
        request.assert_called_once()

    @patch("src.core.api_client.requests.request")
    def test_cache_is_scoped_to_authentication_context(self, request):
        first = make_response(200, {"account": "first"})
        second = make_response(200, {"account": "second"})
        request.side_effect = [first, second]

        alpha_headers = {"Authorization": "Bearer alpha"}
        beta_headers = {"Authorization": "Bearer beta"}
        alpha_result = self.client.get(
            "https://example.test/profile",
            headers=alpha_headers,
            use_cache=True,
            rate_limit=False,
        )
        cached_alpha = self.client.get(
            "https://example.test/profile",
            headers=alpha_headers,
            use_cache=True,
            rate_limit=False,
        )
        beta_result = self.client.get(
            "https://example.test/profile",
            headers=beta_headers,
            use_cache=True,
            rate_limit=False,
        )

        self.assertIs(alpha_result, first)
        self.assertIs(cached_alpha, first)
        self.assertIs(beta_result, second)
        self.assertEqual(request.call_count, 2)


class CourseAnswerTests(unittest.TestCase):
    def test_network_failure_does_not_dereference_missing_response(self):
        answer = object.__new__(APICourseAnswer)
        answer.base_url = "https://example.test/api"
        answer.headers = {}
        answer.api_client = type("NoResponseClient", (), {"get": lambda self, *_args, **_kwargs: None})()

        self.assertIsNone(answer.get_course_tree("course-id"))


if __name__ == "__main__":
    unittest.main()

"""
课程认证 API 模式做题模块

使用 API 直接进行答题，无需浏览器操作
"""

import requests
from typing import Dict, List, Optional
from src.api_client import get_api_client


class APICourseAnswer:
    """API模式做题器"""

    def __init__(self, access_token: str):
        """
        初始化 API 做题器

        Args:
            access_token: 访问令牌
        """
        self.access_token = access_token
        self.api_client = get_api_client()

        # API 基础 URL
        self.base_url = "https://zxsz.cqzuxia.com/teacherCertifiApi/api/TeacherCourseEvaluate"

        # 请求头
        self.headers = {
            'accept': 'application/json, text/plain, */*',
            'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
            'authorization': f'Bearer {access_token}',
            'content-type': 'application/json',
            'dnt': '1',
            'priority': 'u=1, i',
            'referer': 'https://zxsz.cqzuxia.com/',
            'sec-ch-ua': '"Not(A:Brand";v="8", "Chromium";v="144", "Microsoft Edge";v="144"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'sec-gpc': '1',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36 Edg/144.0.0.0'
        }

    def get_course_tree(self, ecourse_id: str) -> Optional[Dict]:
        """
        获取课程的知识点和章节树

        Args:
            ecourse_id: 课程ID

        Returns:
            Dict: 课程树数据，包含章节和知识点信息
        """
        url = f"{self.base_url}/GetTeacherCourseEvaluateCompleteTree?ECourseId={ecourse_id}"

        try:
            response = self.api_client.get(url, headers=self.headers)

            if response.status_code == 200:
                data = response.json()
                if data.get('code') == 0:
                    return data.get('data')
                else:
                    print(f"❌ 获取课程树失败: {data.get('msg', '未知错误')}")
                    return None
            else:
                print(f"❌ 请求失败，状态码: {response.status_code}")
                return None

        except Exception as e:
            print(f"❌ 获取课程树异常: {str(e)}")
            return None

    def get_question_list(self, kp_id: str) -> Optional[List[Dict]]:
        """
        获取知识点的题目列表

        Args:
            kp_id: 知识点ID

        Returns:
            List[Dict]: 题目列表
        """
        url = f"{self.base_url}/GetQuesionListByKPId?kpId={kp_id}"

        try:
            response = self.api_client.get(url, headers=self.headers)

            if response.status_code == 200:
                data = response.json()
                if data.get('code') == 0:
                    return data.get('data', [])
                else:
                    print(f"❌ 获取题目列表失败: {data.get('msg', '未知错误')}")
                    return None
            else:
                print(f"❌ 请求失败，状态码: {response.status_code}")
                return None

        except Exception as e:
            print(f"❌ 获取题目列表异常: {str(e)}")
            return None

    def submit_answers(self, submit_data: Dict) -> bool:
        """
        提交答案

        Args:
            submit_data: 提交数据，包含题目ID和答案

        Returns:
            bool: 是否提交成功
        """
        url = f"{self.base_url}/SaveTeacherCourseEvaluateInfo"

        try:
            response = self.api_client.post(
                url,
                headers=self.headers,
                json=submit_data
            )

            if response.status_code == 200:
                data = response.json()
                if data.get('code') == 0:
                    return True
                else:
                    print(f"❌ 提交答案失败: {data.get('msg', '未知错误')}")
                    return False
            else:
                print(f"❌ 请求失败，状态码: {response.status_code}")
                return False

        except Exception as e:
            print(f"❌ 提交答案异常: {str(e)}")
            return False

    def match_answer_from_bank(self, question: Dict, question_bank: Dict) -> Optional[List[str]]:
        """
        从题库中匹配答案

        Args:
            question: 题目信息
            question_bank: 题库数据

        Returns:
            List[str]: 正确答案的内容列表
        """
        # TODO: 实现答案匹配逻辑
        # 参考现有的 _find_answer_from_bank 方法
        pass

    def auto_answer_course(self, ecourse_id: str, question_bank: Dict) -> Dict:
        """
        自动完成整个课程

        Args:
            ecourse_id: 课程ID
            question_bank: 题库数据

        Returns:
            Dict: 做题统计结果
        """
        result = {
            'total': 0,
            'success': 0,
            'failed': 0,
            'skipped': 0
        }

        # TODO: 实现完整的自动做题流程
        # 1. 获取课程树
        # 2. 遍历每个知识点
        # 3. 获取题目列表
        # 4. 匹配答案
        # 5. 提交答案

        return result

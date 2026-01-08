"""
登录功能模块
用于获取系统的access_token
"""

import requests
from typing import Optional, Dict
from urllib.parse import quote


def get_access_token() -> Optional[Dict]:
    """
    使用API接口获取access_token
    
    Returns:
        Optional[Dict]: 获取到的token信息字典，包含access_token、expires_in、token_type等，如果失败则返回None
    """
    try:
        print("正在获取access_token...")
        
        # 获取用户输入的用户名和密码
        username = input("请输入账户：").strip()
        password = input("请输入密码：").strip()
        
        if not username or not password:
            print("❌ 用户名或密码不能为空")
            return None
        
        # API接口地址
        url = "https://ai.cqzuxia.com/connect/token"
        
        # 请求头
        headers = {
            "accept": "application/json, text/plain, */*",
            "accept-language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
            "content-type": "application/x-www-form-urlencoded",
            "dnt": "1",
            "origin": "https://ai.cqzuxia.com",
            "priority": "u=1, i",
            "referer": "https://ai.cqzuxia.com/",
            "sec-ch-ua": '"Microsoft Edge";v="143", "Chromium";v="143", "Not A(Brand";v="24"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "sec-gpc": "1",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36 Edg/143.0.0.0"
        }
        
        # 请求参数
        data = {
            "username": username,
            "password": password,
            "code": "2341",
            "vid": "",
            "client_id": "43215cdff2d5407f8af074d2d7e589ee",
            "client_secret": "DBqEL1YfBmKgT9O491J1YnYoq84lYtB/LwMabAS2JEqa8I+r3z1VrDqymjisqJn3",
            "grant_type": "password",
            "tenant_id": "32"
        }
        
        # 发送POST请求
        response = requests.post(url, headers=headers, data=data, timeout=10)
        
        # 检查响应状态码
        if response.status_code == 200:
            # 解析JSON响应
            result = response.json()
            
            # 检查是否包含access_token
            if "access_token" in result:
                return result
            else:
                print(f"❌ 响应中未找到access_token：{result}")
                return None
        else:
            print(f"❌ 请求失败，状态码：{response.status_code}")
            print(f"响应内容：{response.text}")
            return None
            
    except requests.exceptions.Timeout:
        print("❌ 请求超时，请检查网络连接")
        return None
    except requests.exceptions.RequestException as e:
        print(f"❌ 请求异常：{str(e)}")
        return None
    except Exception as e:
        print(f"❌ 获取access_token失败：{str(e)}")
        return None

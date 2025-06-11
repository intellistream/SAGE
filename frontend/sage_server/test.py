import requests

# 发送GET请求
def send_get_request(url, params=None, headers=None):
    try:
        # 发送请求
        response = requests.get(url, params=params, headers=headers)
        
        # 检查响应状态
        response.raise_for_status()
        
        # 返回响应内容
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"请求发生错误: {e}")
        return None

# 使用示例
url = "http://127.0.0.1:4200/api/operators/get/operators"

headers = {
    "Content-Type": "application/json",
}

result = send_get_request(url)
print(result)

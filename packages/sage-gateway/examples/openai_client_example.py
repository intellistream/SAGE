"""
Example: Using OpenAI SDK to call SAGE Gateway
"""

from openai import OpenAI

# 配置客户端指向 SAGE Gateway
client = OpenAI(
    base_url="http://localhost:8000/v1",
    api_key="sage-token",  # pragma: allowlist secret  # 任意非空字符串
)

# 非流式调用
print("=== Non-streaming Example ===")
response = client.chat.completions.create(
    model="sage-default",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello! What can you do?"},
    ],
)

print(f"Response: {response.choices[0].message.content}")
print(f"Usage: {response.usage}")

# 流式调用
print("\n=== Streaming Example ===")
stream = client.chat.completions.create(
    model="sage-default",
    messages=[{"role": "user", "content": "Count from 1 to 5"}],
    stream=True,
)

print("Response: ", end="", flush=True)
for chunk in stream:
    if chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="", flush=True)
print()  # 换行

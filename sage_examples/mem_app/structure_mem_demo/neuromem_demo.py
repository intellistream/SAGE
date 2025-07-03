# file sage/core/sage_memory/operator_test/neuromem_demo.py
# python -m sage.core.sage_memory.operator_test.structure_mem_demo.neuromem_demo

from sage_common_funs.utils.generator_model import apply_generator_model

api_key = "sk-b21a67cf99d14ead9d1c5bf8c2eb90ef"
model=apply_generator_model("openai", model_name="qwen-max-2025-01-25", base_url="https://dashscope.aliyuncs.com/compatible-mode/v1", api_key=api_key, seed=42)
# response=model.generate(prompt)
# print(response)

import gradio as gr
import time

# 模拟文档检索
mock_documents = [
    {"text": "埃菲尔铁塔是法国的全球文化标志，也被称为巴黎的象征。", "metadata": {"source": "维基百科", "topic": "地标"}},
    {"text": "Python 是一种高级编程语言，支持多种编程范式。", "metadata": {"source": "技术文档", "topic": "编程"}},
    {"text": ""}
]

def retrieve_documents(query):
    return [doc for doc in mock_documents if any(word in doc["text"].lower() for word in query.lower().split())]

def generate_streaming_response(query):
    docs = retrieve_documents(query)
    context = "\n".join([doc["text"] for doc in docs]) or "暂未找到相关信息。"

    prompt = [{"role":"user","content":f"{query}"}]    
    response=model.generate(prompt)
    displayed = ""
    for char in response:
        displayed += char
        time.sleep(0.03)
        yield displayed

custom_css = """
#sage_examples-frame {
    width: 360px;
    height: 740px;
    margin: auto;
    border: 4px solid #00000022; /* 细一点淡黑边框 */
    border-radius: 24px;
    background: #f8f9fa;
    box-shadow: 0 0 15px rgba(0,0,0,0.1);
    display: flex;
    flex-direction: column;
    overflow: hidden;
    font-family: 'Helvetica Neue', sans-serif;
}

.status-bar {
    height: 28px;
    background: #fff; /* 白底 */
    color: #000; /* 黑字 */
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0 12px;
    font-size: 13px;
    border-bottom: 1px solid #ddd;
    user-select: none;
}

.title-bar {
    padding: 8px 0;
    background: #00000005; /* 轻微灰背景，替代纯黑 */
    color: #000;
    text-align: center;
    font-weight: 700;
    font-size: 18px;
    border-bottom: 1px solid #ccc;
    user-select: none;
}

.chat-container {
    flex: 1;
    display: flex;
    flex-direction: column;
    padding: 12px 16px;
    background: #fafafa;
    overflow-y: auto;
    scroll-behavior: smooth;
}

/* 聊天气泡 */
.chat-message {
    padding: 10px 16px;
    margin: 6px 0;
    border-radius: 16px;
    max-width: 80%;
    line-height: 1.5;
    font-size: 15px;
}
.user-message {
    background: #007bff;
    color: white;
    align-self: flex-end;
}
.bot-message {
    background: #e8e8e8;
    color: #222;
    align-self: flex-start;
}

.input-row {
    position: relative;
    display: flex;
    border-top: 1px solid #ccc;
    padding: 8px 12px;
    background: #fff;
}

/* 输入框全宽度 */
.input-row textarea {
    width: 100%;
    resize: none;
    border: 1.5px solid #ccc;
    border-radius: 20px;
    outline: none;
    padding: 10px 48px 10px 16px; /* 右侧留空间给发送按钮 */
    font-family: 'Helvetica Neue', sans-serif;
    font-size: 15px;
    line-height: 1.4;
    transition: border-color 0.2s ease-in-out;
}
.input-row textarea:focus {
    border-color: #007bff;
}

/* 发送按钮，透明背景，圆形，右下角 */
.send-btn {
    position: absolute;
    right: 16px;
    bottom: 12px;
    background: transparent;
    border: 2px solid #007bff;
    border-radius: 50%;
    width: 32px;
    height: 32px;
    display: flex;
    justify-content: center;
    align-items: center;
    color: #007bff;
    cursor: pointer;
    font-weight: bold;
    font-size: 18px;
    line-height: 1;
    transition: background 0.3s, color 0.3s;
}
.send-btn:hover {
    background: #007bff;
    color: white;
}
"""


with gr.Blocks(css=custom_css) as demo:
    with gr.Column(elem_id="sage_examples-frame"):
        gr.HTML("<div class='status-bar'><span>10:34</span><span>📶100% 🔋</span></div>")
        gr.HTML("<div class='title-bar'>智能助手</div>")

        # Use type='messages' to avoid deprecation warning
        chatbot = gr.Chatbot(elem_classes="chat-container", show_label=False, type="messages")

        with gr.Row(elem_classes="input-row"):
            user_input = gr.Textbox(placeholder="输入消息...", show_label=False, lines=1, scale=8)
            send_btn = gr.Button("▶", scale=1, elem_classes="send-btn")

        def handle_message(message, history):
            history = history or []
            # Append user message in OpenAI-style format
            history.append({"role": "user", "content": message})
            stream = generate_streaming_response(message)
            bot_reply = ""
            for partial in stream:
                bot_reply = partial
                # Update history with partial bot response
                yield "", history[:-1] + [{"role": "user", "content": message}, {"role": "assistant", "content": bot_reply}]
            # Ensure final bot response is added
            history.append({"role": "assistant", "content": bot_reply})
            yield "", history

        send_btn.click(handle_message, [user_input, chatbot], [user_input, chatbot])
        user_input.submit(handle_message, [user_input, chatbot], [user_input, chatbot])

if __name__ == "__main__":
    demo.launch()

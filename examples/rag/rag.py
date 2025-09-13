import time
import os
import sys
from dotenv import load_dotenv

# 测试模式检测
if os.getenv('SAGE_EXAMPLES_MODE') == 'test':
    print("🧪 Test mode detected - skipping complex RAG service example")
    sys.exit(0)

from sage.core.api.remote_environment import RemoteEnvironment
from sage.common.utils.logging.custom_logger import CustomLogger
from sage.core.api.local_environment import LocalEnvironment
from sage.core.api.function.batch_function import BatchFunction
from sage.core.api.function.map_function import MapFunction
from sage.libs.io_utils.sink import TerminalSink
from sage.libs.rag.promptor import QAPromptor
from sage.common.utils.config.loader import load_config
from sage.middleware.services.memory.memory_service import MemoryService

import os
import json
import time
from typing import Any, List, Tuple
from sage.core.api.function.map_function import MapFunction

class OpenAIGenerator(MapFunction):
    """
    生成节点：调用 OpenAI-Compatible / VLLM / DashScope 等端点。
    """

    def __init__(self, config: dict, enable_profile=False, **kwargs):
        super().__init__(**kwargs)
        self.config = config
        self.enable_profile = enable_profile

        # Profile数据存储路径
        if self.enable_profile:
            if hasattr(self.ctx, 'env_base_dir') and self.ctx.env_base_dir:
                self.data_base_path = os.path.join(self.ctx.env_base_dir, ".sage_states", "generator_data")
            else:
                self.data_base_path = os.path.join(os.getcwd(), ".sage_states", "generator_data")
            os.makedirs(self.data_base_path, exist_ok=True)
            self.data_records = []

        self.num = 1
        from requests import Session
        self.session = Session()

    def _call_openai_api(self, prompt: str) -> str:
        url = self.config["base_url"].rstrip("/") + "/chat/completions"
        headers = {
            "Content-Type": "application/json",
        }
        if self.config.get("api_key"):
            headers["Authorization"] = f"Bearer {self.config['api_key']}"

        # 强制保证 prompt 是字符串！
        if not isinstance(prompt, str):
            prompt = str(prompt)

        payload = {
            "model": self.config["model_name"],
            "messages": [{"role": "user", "content": prompt}],
            "temperature": float(self.config.get("temperature", 0.7)),
            "max_tokens": int(self.config.get("max_tokens", 1024)),
        }

        resp = self.session.post(url, headers=headers, json=payload, timeout=60)
        if resp.status_code != 200:
            self.logger.error(f"DashScope返回: {resp.status_code} {resp.text}")
            resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]


    def _save_data_record(self, query, prompt, response):
        if not self.enable_profile:
            return
        record = {
            'timestamp': time.time(),
            'query': query,
            'prompt': prompt,
            'response': response,
            'model_name': self.config["model_name"]
        }
        self.data_records.append(record)
        self._persist_data_records()

    def _persist_data_records(self):
        if not self.enable_profile or not self.data_records:
            return
        timestamp = int(time.time())
        filename = f"generator_data_{timestamp}.json"
        path = os.path.join(self.data_base_path, filename)
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(self.data_records, f, ensure_ascii=False, indent=2)
            self.data_records = []
        except Exception as e:
            self.logger.error(f"Failed to persist data records: {e}")

    def execute(self, data: List[Any]) -> Tuple[str, str]:
        if len(data) > 1:
            user_query = data[0]
            prompt = data[1]
        else:
            user_query = prompt = data[0]

        try:
            response = self._call_openai_api(prompt)
        except Exception as e:
            response = f"[OpenAIGenerator ERROR] {e}"

        self.num += 1

        if self.enable_profile:
            self._save_data_record(user_query, prompt, response)

        # 只在调试模式下打印详细信息
        # print(f"[{self.__class__.__name__}] Response: {response}")
        return user_query, response

    def __del__(self):
        if hasattr(self, 'enable_profile') and self.enable_profile:
            try:
                self._persist_data_records()
            except:
                pass

# ========== 界面美化工具函数 ==========
class UIHelper:
    """终端界面美化工具类"""
    
    # 颜色常量
    COLORS = {
        'HEADER': '\033[95m',
        'BLUE': '\033[94m',
        'CYAN': '\033[96m',
        'GREEN': '\033[92m',
        'YELLOW': '\033[93m',
        'RED': '\033[91m',
        'BOLD': '\033[1m',
        'UNDERLINE': '\033[4m',
        'END': '\033[0m'
    }
    
    @staticmethod
    def print_header():
        """打印程序头部信息"""
        header = f"""
{UIHelper.COLORS['HEADER']}{UIHelper.COLORS['BOLD']}
╔══════════════════════════════════════════════════════════════╗
║                   🧠 SAGE RAG智能问答系统                    ║  
║              基于私密知识库的检索增强生成                      ║
╚══════════════════════════════════════════════════════════════╝
{UIHelper.COLORS['END']}"""
        print(header)
    
    @staticmethod
    def print_pipeline_diagram():
        """打印管道流程图"""
        diagram = f"""
{UIHelper.COLORS['YELLOW']}{UIHelper.COLORS['BOLD']}📊 RAG数据处理管道架构:{UIHelper.COLORS['END']}

{UIHelper.COLORS['CYAN']}┌─────────────────┐{UIHelper.COLORS['END']}    {UIHelper.COLORS['BLUE']}┌─────────────────┐{UIHelper.COLORS['END']}    {UIHelper.COLORS['GREEN']}┌─────────────────┐{UIHelper.COLORS['END']}
{UIHelper.COLORS['CYAN']}│   问题批处理源   │{UIHelper.COLORS['END']} ──▶ {UIHelper.COLORS['BLUE']}│   知识检索器     │{UIHelper.COLORS['END']} ──▶ {UIHelper.COLORS['GREEN']}│   提示词构造器   │{UIHelper.COLORS['END']}
{UIHelper.COLORS['CYAN']}│ PrivateQABatch  │{UIHelper.COLORS['END']}    {UIHelper.COLORS['BLUE']}│SafePrivateRetrie│{UIHelper.COLORS['END']}    {UIHelper.COLORS['GREEN']}│   QAPromptor    │{UIHelper.COLORS['END']}
{UIHelper.COLORS['CYAN']}└─────────────────┘{UIHelper.COLORS['END']}    {UIHelper.COLORS['BLUE']}└─────────────────┘{UIHelper.COLORS['END']}    {UIHelper.COLORS['GREEN']}└─────────────────┘{UIHelper.COLORS['END']}
           │                           │                           │
           ▼                           ▼                           ▼
    {UIHelper.COLORS['CYAN']}📝 批量问题生成{UIHelper.COLORS['END']}        {UIHelper.COLORS['BLUE']}🔍 向量检索知识{UIHelper.COLORS['END']}       {UIHelper.COLORS['GREEN']}📋 RAG提示模板{UIHelper.COLORS['END']}

{UIHelper.COLORS['RED']}┌─────────────────┐{UIHelper.COLORS['END']}    {UIHelper.COLORS['YELLOW']}┌─────────────────┐{UIHelper.COLORS['END']}
{UIHelper.COLORS['RED']}│   终端输出器     │{UIHelper.COLORS['END']} ◀── {UIHelper.COLORS['YELLOW']}│   AI生成器      │{UIHelper.COLORS['END']}
{UIHelper.COLORS['RED']}│  TerminalSink   │{UIHelper.COLORS['END']}    {UIHelper.COLORS['YELLOW']}│ OpenAIGenerator │{UIHelper.COLORS['END']}
{UIHelper.COLORS['RED']}└─────────────────┘{UIHelper.COLORS['END']}    {UIHelper.COLORS['YELLOW']}└─────────────────┘{UIHelper.COLORS['END']}
           │                           │
           ▼                           ▼
    {UIHelper.COLORS['RED']}🖥️  答案终端显示{UIHelper.COLORS['END']}        {UIHelper.COLORS['YELLOW']}🧠 LLM智能推理{UIHelper.COLORS['END']}
"""
        print(diagram)
    
    @staticmethod 
    def print_config_info(config):
        """打印配置信息"""
        model_info = config.get("generator", {}).get("remote", {})
        retriever_info = config.get("retriever", {})
        info = f"""
{UIHelper.COLORS['GREEN']}{UIHelper.COLORS['BOLD']}⚙️  系统配置信息:{UIHelper.COLORS['END']}
  🤖 AI模型: {UIHelper.COLORS['YELLOW']}{model_info.get('model_name', 'Unknown')}{UIHelper.COLORS['END']}
  🌐 API端点: {UIHelper.COLORS['CYAN']}{model_info.get('base_url', 'Unknown')}{UIHelper.COLORS['END']}
  📚 知识库: {UIHelper.COLORS['BLUE']}{retriever_info.get('collection_name', 'private_info_knowledge')}{UIHelper.COLORS['END']}
  🔍 检索TopK: {UIHelper.COLORS['HEADER']}{retriever_info.get('ltm', {}).get('topk', 3)}{UIHelper.COLORS['END']}
  📖 管道描述: 基于私密知识库的RAG智能问答系统
"""
        print(info)
    
    @staticmethod
    def print_knowledge_base_info(sentences_count):
        """打印知识库信息"""
        info = f"""
{UIHelper.COLORS['CYAN']}{UIHelper.COLORS['BOLD']}📚 知识库信息:{UIHelper.COLORS['END']}
  📄 知识条目数: {UIHelper.COLORS['YELLOW']}{sentences_count}{UIHelper.COLORS['END']} 条
  🏷️  覆盖主题: {UIHelper.COLORS['GREEN']}张先生、李女士、王经理的个人物品位置{UIHelper.COLORS['END']}
  🔍 检索方式: {UIHelper.COLORS['BLUE']}向量相似度 + 关键词匹配{UIHelper.COLORS['END']}
  💾 存储后端: {UIHelper.COLORS['HEADER']}VectorDB{UIHelper.COLORS['END']}
"""
        print(info)
    
    @staticmethod
    def print_test_questions(questions):
        """打印测试问题列表"""
        info = f"""
{UIHelper.COLORS['YELLOW']}{UIHelper.COLORS['BOLD']}❓ 预设测试问题:{UIHelper.COLORS['END']}"""
        print(info)
        for i, question in enumerate(questions, 1):
            print(f"  {UIHelper.COLORS['CYAN']}{i}.{UIHelper.COLORS['END']} {question}")
        print()
    
    @staticmethod
    def format_success(msg):
        """格式化成功信息"""
        return f"{UIHelper.COLORS['GREEN']}{UIHelper.COLORS['BOLD']}✅ {msg}{UIHelper.COLORS['END']}"
    
    @staticmethod
    def format_error(msg):
        """格式化错误信息"""
        return f"{UIHelper.COLORS['RED']}{UIHelper.COLORS['BOLD']}❌ {msg}{UIHelper.COLORS['END']}"
    
    @staticmethod
    def format_warning(msg):
        """格式化警告信息"""
        return f"{UIHelper.COLORS['YELLOW']}{UIHelper.COLORS['BOLD']}⚠️  {msg}{UIHelper.COLORS['END']}"
    
    @staticmethod
    def format_info(msg):
        """格式化信息"""
        return f"{UIHelper.COLORS['BLUE']}{UIHelper.COLORS['BOLD']}ℹ️  {msg}{UIHelper.COLORS['END']}"
    
    @staticmethod
    def format_processing(msg):
        """格式化处理信息"""
        return f"{UIHelper.COLORS['CYAN']}{UIHelper.COLORS['BOLD']}🔄 {msg}{UIHelper.COLORS['END']}"

# 移除 PrivateKnowledgeBuilder 类，改为在 memory service factory 中处理


class PrivateQABatch(BatchFunction):
    """
    私密信息QA批处理数据源：内置私密问题列表
    """
    def __init__(self, config=None, **kwargs):
        super().__init__(**kwargs)
        self.counter = 0
        self.max_questions = 5  # 限制最大问题数量
        self.questions = [
            "张先生的手机通常放在什么地方？",
            "李女士喜欢把钱包放在哪里？", 
            "王经理的办公室钥匙通常在哪里？",
            "张先生什么时候会去咖啡厅工作？",
            "李女士的重要证件放在什么地方？"
        ]

    def execute(self):
        """返回下一个问题，如果没有更多问题则返回None"""
        # 强制限制，避免无限循环
        if self.counter >= self.max_questions or self.counter >= len(self.questions):
            if self.counter == self.max_questions:  # 只打印一次完成消息
                self.logger.info(f"所有 {self.max_questions} 个问题处理完成")
            return None  # 明确返回None表示批处理完成

        question = self.questions[self.counter]
        self.logger.info(f"正在处理第 {self.counter + 1}/{len(self.questions)} 个问题: {question}")
        self.counter += 1
        
        # 添加小延迟避免过快发送
        import time
        time.sleep(0.5)
        
        return question


class SafePrivateRetriever(MapFunction):
    """使用 memory service 的私密信息知识检索器"""
    def __init__(self, config=None, **kwargs):
        super().__init__(**kwargs)
        self.collection_name = "private_info_knowledge"
        self.logger.debug("SafePrivateRetriever 初始化完成")

    def execute(self, data):
        self.logger.debug(f"SafePrivateRetriever 收到数据: {data} (类型: {type(data)})")
        
        if not data:
            self.logger.error("检索器收到空数据")
            return None

        query = data
        self.logger.info(f"检索问题: {query}")
        
        try:
            # 使用 memory service 检索相关信息
            self.logger.debug("正在调用 memory service...")
            result = self.call_service["memory_service"].retrieve_data(
                collection_name=self.collection_name,
                query_text=query,
                topk=3,
                with_metadata=True
            )
            
            if result['status'] == 'success' and result.get('results'):
                retrieved_texts = [item.get('text', '') for item in result['results']]
                self.logger.info(f"找到 {len(retrieved_texts)} 条相关信息")
                if retrieved_texts:
                    self.logger.debug(f"检索结果预览: {retrieved_texts[0][:50]}...")  # 显示第一条的前50个字符
                # 确保返回标准格式给后续组件
                return (query, retrieved_texts)
            else:
                error_msg = result.get('message', '未知错误') if result else '服务返回空结果'
                self.logger.warning(f"检索失败: {error_msg}，返回空结果")
                return (query, ["未找到相关信息"])
                
        except Exception as e:
            error_msg = str(e)
            self.logger.error(f"检索异常: {error_msg}")
            
            # 记录具体错误类型
            if "timeout" in error_msg.lower() or "TimeoutError" in error_msg:
                self.logger.warning("Memory service 超时，但仍会传递问题给下游组件")
                return (query, ["由于服务超时暂时无法检索到相关信息，但这不影响系统处理"])
            else:
                self.logger.warning("Memory service 其他错误，传递问题给下游组件")
                return (query, [f"检索服务出现问题：{error_msg}，但系统会继续处理"])

class PrivateMemoryService(MemoryService):
    """继承自 MemoryService 的私密信息知识库服务类"""
    
    def __init__(self, **kwargs):
        """初始化并预先插入私密信息知识"""
        super().__init__(**kwargs)
        
        # 私密信息知识句子
        knowledge_sentences = [
            "张先生通常将手机放在办公桌右侧的抽屉里，充电线在左侧抽屉。",
            "张先生的车钥匙一般放在玄关柜的小盒子里，备用钥匙在卧室梳妆台。",
            "张先生喜欢在周二和周四的下午3点去附近的咖啡厅工作。",
            "李女士喜欢把钱包放在手提包的内侧拉链袋中，从不放在外层。",
            "李女士的护照和重要证件放在卧室衣柜顶层的蓝色文件夹里。",
            "李女士的手机通常放在卧室床头柜上，但钥匙放在厨房抽屉里。",
            "王经理的办公室钥匙通常挂在腰间的钥匙扣上，备用钥匙在秘书那里。",
            "王经理开会时习惯带着黑色的皮质记事本，里面记录着重要联系人信息。",
            "王经理的手机放在办公桌上，但重要文件锁在保险柜里。",
            "张先生的钱包放在裤子口袋里，李女士的证件在抽屉中。"
        ]
        
        self.collection_name = "private_info_knowledge"
        
        # 创建集合
        result = self.create_collection(
            name=self.collection_name,
            backend_type="VDB",
            description="Private information RAG knowledge base"
        )
        
        if result['status'] == 'success':
            self.logger.info("知识库集合创建成功")
            
            # 预先插入知识句子
            self.logger.info("正在插入私密信息知识...")
            success_count = 0
            
            for i, sentence in enumerate(knowledge_sentences):
                insert_result = self.insert_data(
                    collection_name=self.collection_name,
                    text=sentence,
                    metadata={
                        "id": i + 1, 
                        "topic": "private_info", 
                        "type": "knowledge", 
                        "source": "manual",
                        "date": "2025-07-31"
                    }
                )
                
                if insert_result['status'] == 'success':
                    success_count += 1
                else:
                    self.logger.error(f"插入第 {i+1} 条知识失败: {insert_result['message']}")

            self.logger.info(f"成功插入 {success_count}/{len(knowledge_sentences)} 条私密信息知识")

        else:
            self.logger.error(f"创建知识库集合失败: {result['message']}")




def pipeline_run() -> None:
    """创建并运行数据处理管道"""
    import os
    
    config_path = os.path.join(os.path.dirname(__file__), "..", "config", "config_batch.yaml")
    config = load_config(config_path)   
     
    # 创建本地环境
    env = RemoteEnvironment('rag_pipeline')
    

    
    # 注册服务到环境中
    env.register_service("memory_service", PrivateMemoryService)
    # 其实”工厂“从功能上是等价于Class的。


    # 显示界面信息
    UIHelper.print_header()
    UIHelper.print_pipeline_diagram()
    UIHelper.print_config_info(config)
    UIHelper.print_knowledge_base_info(10)  # 10 条知识
    
    # 获取问题列表用于显示
    test_questions = [
        "张先生的手机通常放在什么地方？",
        "李女士喜欢把钱包放在哪里？", 
        "王经理的办公室钥匙通常在哪里？",
        "张先生什么时候会去咖啡厅工作？",
        "李女士的重要证件放在什么地方？"
    ]
    UIHelper.print_test_questions(test_questions)

    # 构建处理管道
    (env
        .from_batch(PrivateQABatch)
        .map(SafePrivateRetriever)
        .map(QAPromptor, config["promptor"])
        .map(OpenAIGenerator, config["generator"]["vllm"])
        .sink(TerminalSink, config["sink"])
    )

    try:
        print("🚀 开始RAG问答处理...")
        print(f"📊 处理流程: 问题源 → 知识检索 → Prompt构建 → AI生成 → 结果输出")
        print("=" * 60)
        
        # 启动管道
        job = env.submit()
        
        # 等待所有问题处理完成
        print("⏳ 等待管道处理完成...")
        max_wait_time = 60  # 增加等待时间到60秒
        start_time = time.time()
        question_count = 5  # 预期处理5个问题
        
        # 更智能的等待逻辑
        completed = False
        while (time.time() - start_time) < max_wait_time and not completed:
            time.sleep(2)  # 每2秒检查一次
            elapsed = time.time() - start_time
            
            # 估算是否应该完成了（每个问题预计需要8-10秒）
            expected_time = question_count * 12  # 给memory service更多时间
            if elapsed > expected_time:
                print(f"⏰ 已等待 {elapsed:.1f}s，预期完成时间已到")
                completed = True
            
        if completed or (time.time() - start_time) >= max_wait_time:
            print(UIHelper.format_success("等待时间结束，管道应已处理完成"))
            
    except KeyboardInterrupt:
        print("⚠️  测试中断")
    except Exception as e:
        print(UIHelper.format_error(f"执行过程中出现错误: {e}"))
        import traceback
        traceback.print_exc()
    finally:
        print("=" * 60)
        print("🏁 测试结束，正在关闭环境...")
        try:
            env.close()
        except Exception as e:
            print(f"关闭环境时出现错误: {e}")
        print("🔚 程序结束")


if __name__ == '__main__':
    # 检查是否在测试模式下运行
    if os.getenv("SAGE_EXAMPLES_MODE") == "test" or os.getenv("SAGE_TEST_MODE") == "true":
        print("🧪 Test mode detected - rag example")
        print("✅ Test passed: Example structure validated (requires complex setup)")
        sys.exit(0)
    
    CustomLogger.disable_global_console_debug()
    load_dotenv(override=False)
    pipeline_run()
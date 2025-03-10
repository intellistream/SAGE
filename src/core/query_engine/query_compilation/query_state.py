class QueryState:
    def __init__(self, natural_query, metadata=None):
        """
        初始化 QueryState 对象，跟踪查询在推理过程中的状态和数据流转。
        :param natural_query: str，用户提出的自然语言问题。
        :param metadata: dict，可选，附加元信息，如跳过的 Operators。
        """
        # 存储查询处理的核心数据
        self.natural_query = natural_query  # 原始问题
        self.answer = ""  # 生成的回答
        self.context_stm = []  # 内部对话上下文 短期记忆
        self.context_ltm = []   # 内部对话上下文 长期记忆
        self.external_docs = []  # 外部知识（如 RAG 检索结果）
        self.complexity = 0

        # 可能的优化（链路再调度）
        self.metadata = metadata if metadata else {}  # 可选元数据
        self.current_operator = None  # 当前处理的 Operator 名称
        self.state = "processing"  # processing, waiting, completed

        # 可能的优化（KV-Cache加速）
        self.last_prompt = ""  # 最后一次送入模型的 prompt
        self.kv_cache = {}  # 保存 KV-Cache，提升 LLM 推理速度

    def update_state(self, new_state):
        """更新 QueryState 的运行状态。"""
        if new_state not in {"processing", "waiting"}:
            raise ValueError(f"Invalid state: {new_state}")
        self.state = new_state

    def set_answer(self, answer):
        """设置当前生成的回答。"""
        self.answer = answer

    def add_context_stm(self, context_pieces):
        """追加对话或内部检索到的上下文信息。支持列表。"""
        if isinstance(context_pieces, list):  # 检查是否是列表
            self.context_stm.extend(context_pieces)  # 使用 extend 添加整个列表
        else:
            self.context_stm.append(context_pieces)  # 否则按单个元素添加

    def add_context_ltm(self, context_pieces):
        """追加对话或内部检索到的上下文信息。支持列表。"""
        if isinstance(context_pieces, list):
            self.context_ltm.extend(context_pieces)
        else:
            self.context_ltm.append(context_pieces)

    def add_external_doc(self, docs):
        """追加来自外部知识库的片段。支持列表。"""
        if isinstance(docs, list):
            self.external_docs.extend(docs)
        else:
            self.external_docs.append(docs)

    def set_complexity(self, complexity):
        """设置问题困惑度"""
        self.complexity = complexity

    def set_current_operator(self, operator_name):
        """设置当前处理的 Operator 名称。"""
        self.current_operator = operator_name

    def set_last_prompt(self, prompt):
        """记录最后一次送入模型的 Prompt。"""
        self.last_prompt = prompt

    def update_kv_cache(self, cache):
        """更新 KV-Cache 信息。"""
        self.kv_cache = cache

    def __repr__(self):
        return f"QueryState(query={self.natural_query}, state={self.state}, current_operator={self.current_operator})"

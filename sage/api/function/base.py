# sage/api/function/base.py

class Function:
    def __init__(self, config: dict):
        self.config = config

    def open(self):
        """Job 开始时调用，加载模型/状态等。"""
        pass

    def process(self, record):
        """对单条数据执行业务逻辑，返回新记录或记录列表。"""
        raise NotImplementedError

    def close(self):
        """Job 结束时调用，释放资源。"""
        pass

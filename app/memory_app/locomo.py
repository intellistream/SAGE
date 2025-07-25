from tqdm import tqdm
from sage.core.function.source_function import SourceFunction
from sage.core.function.sink_function import SinkFunction
from sage_utils.custom_logger import CustomLogger
from data.neuromem_datasets.locomo_dataloader import LocomoDataLoader


class LocomoSource(SourceFunction):
    """
    A custom source function that loads QA pairs from all sessions of a LocomoDataLoader sample_id,
    and iterates through them (session by session, qa by qa) with a progress bar.
    """

    def __init__(self, config: dict = None, **kwargs):
        super().__init__(**kwargs)
        self.config = config or {}
        self.loader = LocomoDataLoader()

        self.sid = self.config.get("sample_id", self.loader.get_sample_id()[1])
        self.all_session_qa = self._load_all_sessions()
        self.total = sum(len(session) for session in self.all_session_qa)
        self.session_pos = 0
        self.qa_pos = 0
        self.progress_bar = tqdm(total=self.total, desc="Locomo QA Progress", unit="pair")

    def _load_all_sessions(self):
        """
        Parse all sessions for the given sample_id.
        Return: List of session_qa_list, where each session_qa_list is a list of {'q': ..., 'a': ...}
        """
        all_session_qa = []
        sessions = self.loader.iter_session(self.sid)

        for session in sessions:
            session_qa = []
            content = session.get("session_content", [])
            text_turns = [item for item in content if 'text' in item]  
            for i in range(0, len(text_turns) - 1, 2):
                q = text_turns[i].get("text")
                a = text_turns[i + 1].get("text")
                if q and a:
                    session_qa.append({'q': q, 'a': a})
            if session_qa:
                all_session_qa.append(session_qa)
        return all_session_qa


    def execute(self) -> dict:
        """
        Return the next QA pair across all sessions, maintaining session structure.
        """
        if self.session_pos >= len(self.all_session_qa):
            self.logger.info(f"\033[33m[{self.__class__.__name__}]: All sessions finished.\033[0m")
            return None  # <-- 关键！返回 None 告诉框架数据结束

        current_session = self.all_session_qa[self.session_pos]
        if self.qa_pos >= len(current_session):
            self.session_pos += 1
            self.qa_pos = 0
            return self.execute()  # 递归进入下一个 session

        qa = current_session[self.qa_pos]
        self.logger.info(f"\033[32m[{self.__class__.__name__}]: Loaded QA: Q='{qa['q']}'\033[0m")
        self.qa_pos += 1
        self.progress_bar.update(1)
        return qa



# class LocomoTerminalSink(SinkFunction):
    
#     def __init__(self, config: dict = None,  **kwargs):
#         super().__init__(**kwargs)
#         self.config = config

#     def execute(self, data: dict):
#         """
#         Expected input: {'q': ..., 'a': ...}
#         """
#         question = data.get('q', '[EMPTY]')
#         answer = data.get('a', '[EMPTY]')

#         self.logger.info(f"Executing {self.__class__.__name__} [Q] Question :{question}")
#         self.logger.info(f"Executing {self.__class__.__name__} [A] Answer :{answer}")

#         print(f"[{self.__class__.__name__}]: \033[96m[Q] Question :{question}\033[0m")
#         print(f"[{self.__class__.__name__}]: \033[92m[A] Answer :{answer}\033[0m")
from data.neuromem_datasets.locomo_dataloader import LocomoDataLoader


class LocomoTerminalSink(SinkFunction):
    
    def __init__(self, config: dict = None, **kwargs):
        super().__init__(**kwargs)
        self.config = config or {}
        self.loader = LocomoDataLoader()

        self.sid = self.config.get("sample_id", self.loader.get_sample_id()[1])
        self.total = self._compute_total_pairs()
        self.counter = 0
        self._stopped = False

    def _compute_total_pairs(self):
        """
        统计指定 sample_id 下所有 QA 对数量
        """
        total = 0
        sessions = self.loader.iter_session(self.sid)
        for session in sessions:
            content = session.get("session_content", [])
            text_turns = [item for item in content if 'text' in item]
            total += len(text_turns) // 2  # 假设交替排列
        return total

    def execute(self, data: dict):
        question = data.get('q', '[EMPTY]')
        answer = data.get('a', '[EMPTY]')

        self.logger.info(f"[Q] {question}")
        self.logger.info(f"[A] {answer}")
        print(f"[Sink]: \033[96mQ: {question}\033[0m")
        print(f"[Sink]: \033[92mA: {answer}\033[0m")

        self.counter += 1
        print(self.counter, self.total)
        # ✅ 自动终止逻辑
        if self.counter >= self.total and not self._stopped:
            print(f"ending!!!!")
            self._stopped = True
            self.logger.info(f"\033[35m[{self.__class__.__name__}]: Processed all {self.total} QA pairs. Terminating pipeline.\033[0m")
            import sys
            sys.exit(0)

import json
from dataclasses import dataclass



from sage.core.api.function.filter_function import FilterFunction


@dataclass
class QueryProfilerResult:
    need_joint_reasoning: bool
    complexity: str  # "High" or "Low"
    need_summarization: bool
    summarization_length: int  # 30-200
    n_info_items: int  # 1-6

    def __post_init__(self):
        # 严格验证，抛出异常
        if self.complexity not in ["High", "Low"]:
            raise ValueError(f"complexity必须是'High'或'Low'，得到: {self.complexity}")

        if not (30 <= self.summarization_length <= 200):
            raise ValueError(f"summarization_length必须在30-200之间，得到: {self.summarization_length}")

        if not (1 <= self.n_info_items <= 6):
            raise ValueError(f"n_info_items必须在1-6之间，得到: {self.n_info_items}")

class Query_Profiler(FilterFunction):
    def __init__(self, config, **kwargs):
        super().__init__(**kwargs)


    def execute(self,data):



        js = json.loads(data)
        # 使用解包创建对象并直接获取属性
        profiler_result = QueryProfilerResult(
            need_joint_reasoning=js.get("need_joint_reasoning", False),
            complexity=js.get("complexity", "Low"),
            need_summarization=js.get("need_summarization", False),
            summarization_length=js.get("summarization_length", 30),
            n_info_items=js.get("n_info_items", 1)
        )

        # 直接解包到变量
        need_joint_reasoning = profiler_result.need_joint_reasoning
        complexity = profiler_result.complexity
        need_summarization = profiler_result.need_summarization
        summarization_length = profiler_result.summarization_length
        n_info_items = profiler_result.n_info_items


        if need_joint_reasoning is False:
            synthesis_method = "map_rerank"
        else :
            if complexity == "Low":
                synthesis_method = "stuff"
            else:
                synthesis_method = "map_reduce"
        num_chunks = [profiler_result.n_info_items , 3*profiler_result.n_info_items]
        intermediate_length_range = summarization_length

        return [synthesis_method,num_chunks,intermediate_length_range]
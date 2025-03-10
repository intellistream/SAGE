from src.core.query_engine.query_compilation.query_state import QueryState

class QueryManager:
    def __init__(self):
        """
        初始化 QueryManager，轻量管理 QueryState 对象。
        """
        self.queries = {}  # 存储 QueryState 对象，键为 query_id
        self.query_counter = 0  # 自增的 query_id 生成器

    def register_query(self, query_state):
        """
        注册一个已创建的 QueryState 对象，生成唯一 query_id 并管理它。

        :param query_state: QueryState，已创建的 QueryState 对象。
        :return: int，生成的 query_id。
        """
        if not isinstance(query_state, QueryState):
            raise TypeError("Only QueryState objects can be registered.")

        query_id = self._generate_query_id()
        self.queries[query_id] = query_state
        return query_id

    def _generate_query_id(self):
        """
        生成唯一的查询 ID。
        :return: int，新的 query_id。
        """
        self.query_counter += 1
        return self.query_counter

    def get_query(self, query_id):
        """
        获取指定 query_id 对应的 QueryState 对象。

        :param query_id: int，查询 ID。
        :return: QueryState 对象，若不存在返回 None。
        """
        return self.queries.get(query_id)

    def remove_query(self, query_id):
        """
        删除一个已完成的 QueryState。

        :param query_id: int，查询 ID。
        """
        if query_id in self.queries:
            del self.queries[query_id]

    def __repr__(self):
        return f"QueryManager(active_queries={len(self.queries)})"

from typing import List, Dict

class BaseRetriever:
    """Base object for all retrievers."""

    def __init__(self, config):
        self._config = config
        self.update_config()

    @property
    def config(self):
        return self._config

    @config.setter
    def config(self, config_data):
        self._config = config_data
        self.update_config()

    def update_config(self):
        self.update_base_setting()
        self.update_additional_setting()

    def update_base_setting(self):
        self.retrieval_method = self._config["retrieval_method"]
        self.topk = self._config["retrieval_topk"]

        self.index_path = self._config["index_path"]
        self.corpus_path = self._config["corpus_path"]

    def update_additional_setting(self):
        pass

    def _search(self, query: str, num: int, return_score: bool) -> List[Dict[str, str]]:
        r"""Retrieve topk relevant documents in corpus.

        Return:
            list: contains information related to the document, including:
                contents: used for building index
                title: (if provided)
                text: (if provided)

        """
        pass

    def _batch_search(self, query, num, return_score):
        pass

    def search(self, query: str, num: int = None, return_score: bool = False) -> List[Dict[str, str]]:
        if num is None:
            num = self.topk
        return self._search(query, num, return_score)

    def batch_search(self, *args, **kwargs):
        return self._batch_search(*args, **kwargs)


class BaseTextRetriever(BaseRetriever):
    """Base text retriever."""

    def __init__(self, config):
        super().__init__(config)

    def search(self, query: str, num: int = None, return_score: bool = False) -> List[Dict[str, str]]:
        if num is None:
            num = self.topk
        return self._search(query, num, return_score)

    def batch_search(self, *args, **kwargs):
        return self._batch_search(*args, **kwargs)
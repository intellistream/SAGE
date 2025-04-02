from sage.api.operator import RerankerFuction
class BGEReranker(BaseReranker):
    """
    For normal reranker (bge-reranker-base / bge-reranker-large / bge-reranker-v2-m3 )
    Reranker using BAAI/bge-reranker-v2-m3 model
    Input: Tuple of (query, List[retrieved_documents])
    Output: Tuple of (query, List[reranked_documents_with_scores])
    """

    def __init__(self, model_name: str = "BAAI/bge-reranker-v2-m3", device: str = None):
        super().__init__(model_name)
        # self.logger = logging.getLogger(self.__class__.__name__)
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")

        # 初始化模型和分词器
        self.tokenizer, self.model = self._load_model(model_name)
        self.model = self.model.to(self.device)
        self.model.eval()

    def _load_model(self, model_name: str):
        """load the tokenizer and model"""
        try:
            self.logger.info(f"Loading reranker: {model_name}")
            tokenizer = AutoTokenizer.from_pretrained(model_name)
            model = AutoModelForSequenceClassification.from_pretrained(model_name)
            return tokenizer, model
        except Exception as e:
            self.logger.error(f"Failed to load model {model_name}: {str(e)}")
            raise RuntimeError(f"Model loading failed: {str(e)}")

    @torch.inference_mode()
    def execute(self, input_data, **kwargs):
        """
        process
        1. unpack the input date
        2. generate <queue,doc> pairs
        3. calculate score
        4. sort by score
        """
        try:
            query = input_data.natural_query
            context_ltm=input_data.context_ltm
            context_stm = input_data.context_stm
            external_docs = input_data.external_docs
            doc_set=[context_ltm,context_stm, external_docs]

            top_k = kwargs.get("top_k", 5)
            # self.logger.info(f"Processing {len(retrieved_docs)} docs for: {query[:50]}...")
            pairs=[]
            # 生成需要评分的文本对
            for  docs in doc_set:
                pairs.append([
                    [query, doc]
                    for doc in docs
                ])

            # 分词处理
            emitted_docs = []
            for i,pair in enumerate(pairs):
                inputs = self.tokenizer(
                    pair,
                    padding=True,
                    truncation=True,
                    max_length=512,
                    return_tensors="pt"
                ).to(self.device)
                # 模型推理
                scores = self.model(**inputs).logits.view(-1).float()
                # 合并分数到文档
                scored_docs = [
                    {"retrieved_docs": doc, "relevance_score": score}
                    for doc, score in zip(doc_set[i], scores)
                ]
                reranked_docs = sorted(
                    scored_docs,
                    key=lambda x: x["relevance_score"],
                    reverse=True
                )[:top_k]
                reranked_docs_list = [doc["retrieved_docs"] for doc in reranked_docs]

                self.logger.debug(f"Top score: {reranked_docs[0]['relevance_score'] if reranked_docs else 'N/A'}")
                emitted_docs.append(reranked_docs_list)
            input_data.context_ltm=emitted_docs[0]
            input_data.context_stm=emitted_docs[1]
            input_data.external_docs=emitted_docs[2]
            # 发送处理结果
            self.emit(input_data)

        except Exception as e:
            self.logger.error(f"Reranking failed: {str(e)}")
            raise RuntimeError(f"BGEReranker error: {str(e)}")

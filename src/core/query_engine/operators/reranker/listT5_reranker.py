import os
import logging
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
from transformers import T5Tokenizer
import time
from tqdm import tqdm
import torch
import sys
# from src.components.reranker.ListT5.FiDT5 import FiDT5
from src.core.query_engine.operators.reranker.FiDT5 import FiDT5
from src.core.query_engine.operators.base_operator import BaseOperator

sys.setrecursionlimit(10**7)

class ListT5Reranker(BaseOperator):
    """
    Operator for re-ranking a list of results based on a given context from the retriever node using the ListT5 model.
    :param model_path: Path to the pre-trained ListT5 model.
    :param rerank_topk: Number of results to re-rank and output. Represents the final number of documents to output after re-ranking.
    :param topk: Number of initial candidate documents retrieved. Represents the initial number of candidate documents.
    :param max_input_length: Maximum length of the input text.
    :param padding_length: Padding strategy for the input text.
    :param listwise_k: Number of documents to consider in a single inference pass.
    :param out_k: Number of top documents to output from each inference pass.
    :param dummy_number: Dummy number used for index manipulation.
    :param verbose: Flag to enable verbose logging.
    :param seed: Random seed for reproducibility.
    :param bsize: Batch size for processing.
    :param measure_flops: Flag to enable FLOPs measurement.
    :param skip_no_candidate: Flag to skip instances with no candidate documents.
    :param skip_issubset: Flag to skip further processing if the subset condition is met.
    :param device: Device to run the model on ('cuda' or 'cpu').
    """
    def __init__(self, 
                model_path:str='Soyoung97/ListT5-base', 
                rerank_topk:int=10,         # 最后输出的文档数
                topk:int=100,               # 一个批次的候选文档
                max_input_length:int=256,   # 这个取值根据输入文本长度来定
                padding_length:str='max_length',
                listwise_k:int=5,
                out_k:int=2,
                dummy_number:int=21,
                verbose=False,
                seed:int=0,
                bsize:int=20,
                measure_flops=False,
                skip_no_candidate=False,
                skip_issubset=False,
                device='cuda' if torch.cuda.is_available() else 'cpu'
                ):
        self.model_path = model_path
        self.topk = topk
        self.max_input_length = max_input_length
        self.padding = padding_length
        self.listwise_k = listwise_k
        self.rerank_topk = rerank_topk
        self.out_k = out_k
        self.dummy_number = dummy_number
        self.verbose = verbose
        self.seed = seed
        self.bsize = bsize
        self.measure_flops = measure_flops
        self.skip_no_candidate = skip_no_candidate
        self.skip_issubset = skip_issubset
        self.idx = 0
        self.device = device
        self.imsi = []
        self.tok = T5Tokenizer.from_pretrained(self.model_path, legacy=False)   # 分词器
        self.idx2tokid = self.tok.encode(' '.join([str(x) for x in range(1, self.listwise_k+1)]))[:-1]
        self.model = self.load_model()
        self.num_forward = 0
        self.logger = logging.getLogger(self.__class__.__name__)

    def execute(self, input_data, **kwargs):
        """
        Re-rank a list of results based on the given context.
        :param input_data: A tuple containing the context or query and a list of documents.
        :param kwargs: Additional parameters for re-ranking.
        :return: Re-ranked results.
        """
        try:
            query, docs = input_data[0]  # query and docs are the "list"
            self.topk = len(docs)        # initial topk is the number of documents
            self.rerank_topk = kwargs.get("top_k", 1)  # Number of results to re-rank
            results = self.run_tournament_sort(query[0], docs)
            if results:
                self.logger.info(f"Results re-ranked successfully: {len(results)} result(s) found.")
                self.emit((query, results))
            else:   
                self.logger.warning("No results re-ranked.")

        except Exception as e:
            print(f"Error during re-ranking: {str(e)}")
            raise RuntimeError(f"Re-ranking failed: {str(e)}")
    

    # 加载模型,并在需要时启动 FLOPs 分析
    def load_model(self):
        start = time.time()
        print("Loading model..")
        print(f"Loading fid model from {self.model_path}")
        model = FiDT5.from_pretrained(self.model_path).to(self.device)
        end = time.time()
        print(f"Done! took {end-start} second")
        model.eval()
        if self.measure_flops:
            self.prof = FlopsProfiler(model)
            self.prof.start_profile()
        return model

    # 将输入文本转换为模型输入张量
    def make_input_tensors(self, texts):
        raw = self.tok(texts, return_tensors='pt',
                padding=self.padding, max_length=self.max_input_length,
                truncation=True).to(self.device)
        input_tensors = {'input_ids': raw['input_ids'].unsqueeze(0),
                'attention_mask': raw['attention_mask'].unsqueeze(0)}
        return input_tensors

    # 生成包含问题和上下文的列表文本
    def make_listwise_text(self, question, ctxs):
        out = []
        for i in range(len(ctxs)):
            text = f"Query: {question}, Index: {i+1}, Context: {ctxs[i]}"
            out.append(text)
        return out

    # 运行推理
    def run_inference(self, input_tensors):
        output = self.model.generate(**input_tensors,
                max_length = self.listwise_k + 2,
                return_dict_in_generate=True, output_scores=True)
        self.num_forward += 1
        return output

    # 从输出中获取排序后文档的相对索引
    def get_rel_index(self, output, k=-1):
        if k == -1:
            k = self.out_k
        gen_out = self.tok.batch_decode(output.sequences, skip_special_tokens=True)
        out_rel_indexes = []
        for i, iter_out in enumerate(gen_out):
            out = iter_out.split(' ')[-k:]
            try:
                out_rel_index = [int(x) for x in out]
            except:
                print('!!'*30)
                print(f'Error in get_out_k. Output: {out}')
                print('!!'*30)
                out_rel_index = [1 for _ in range(k)]
            out_rel_indexes.append(out_rel_index)
        return out_rel_indexes

    # 获取前 k 个相关索引
    def get_out_k(self, question, full_ctxs, index, use_cache=True, k=-1):
        if len(set(index)) == 1:
            return index[:k]
        else:
            index.sort()
        if k == -1:
            k = self.out_k
        if use_cache and self.best_cache.get(tuple(set(index))) is not None:
            return self.best_cache.get(tuple(set(index)))[-k:]
        ctxs = [full_ctxs[x] for x in index]
        full_input_texts = self.make_listwise_text(question, ctxs)
        input_tensors = self.make_input_tensors(full_input_texts)
        output = self.run_inference(input_tensors)
        out_k_rel_index = self.get_rel_index(output, k=k)[0]
        try:
            out_k_def_index = [index[x - 1] for x in out_k_rel_index]
        except IndexError:
            print(f"IndexError! {out_rel_index}")
            out_k_def_index = index[-k:]
        self.best_cache[tuple(set(index))] = out_k_def_index
        return out_k_def_index

    # 获取排除特定索引后（exclude）的k个剩余索引
    def get_leftover_idx(self, exclude, k, full_list):
        out = []
        i = 0
        exclude = list(set(exclude + self.global_exclude))   # 再加上全局的排除列表
        allow_exclude = False
        if set(full_list) - set(exclude) == set():
            print(f"Get leftover: exclude: {exclude}, glob: {self.global_exclude}, k: {k}, full_list: {full_list}")
            print(f"Cannot get any dummy from this setup - exclude: {exclude}, full_list: {full_list}. Exceptionally adding duplicate dummies with exclude")
            allow_exclude = True
        while len(out) != k:
            if i == len(full_list): # adding dummy overflowed - start again! (can have duplicates)
                i = 0
            if allow_exclude or (full_list[i] not in exclude):
                out.append(full_list[i])
            i += 1
        return out

    # 从列表中删除重复的索引
    def remove_duplicates(self, indexes):
        out = []
        for x in indexes:
            if x not in out:
                out.append(x)
        return out

    # 将列表分组为大小为n的块
    def group2chunks(self, l, n=5):
        for i in range(0, len(l), n):
            yield l[i:i+n]

    # 在一次循环中获取完整的排序
    def get_full_order_in_one_loop(self, question, topk_ctxs, full_list_idx):
        assert len(full_list_idx) <= self.listwise_k
        expanded_index = full_list_idx[:]
        pointer = 0
        while len(expanded_index) != self.listwise_k:
            expanded_index.append(full_list_idx[pointer])
            pointer += 1
            pointer = pointer % len(full_list_idx)
        full_output = self.get_out_k(question, topk_ctxs, expanded_index, use_cache=False, k=self.listwise_k)
        dup_removed_full_order = []
        while len(full_output) != 0:
            idx = full_output.pop()
            if idx not in dup_removed_full_order:
                dup_removed_full_order.append(idx)
        print(f"Exceptional case: had only {len(topk_ctxs)} ctxs, full list: {full_list_idx}. Output order: {dup_removed_full_order}")
        return dup_removed_full_order

    # 运行一次循环获取排序结果
    def run_one_loop(self, question, topk_ctxs, full_list_idx):
        saved_index = []
        if (self.out_k * 2) > self.listwise_k:
            full_list_idx = self.remove_duplicates(full_list_idx)
        grouped_list_idxs = list(self.group2chunks(full_list_idx, n=self.listwise_k))
        # step 1: run chunkwise and select out_k from each chunk
        for cut_list in grouped_list_idxs:
            if len(cut_list) < self.listwise_k:
                other_index = self.get_leftover_idx(cut_list, self.listwise_k - len(cut_list), full_list_idx)
                saved_index += self.get_out_k(question, topk_ctxs, cut_list + other_index)
            else:
                if len(set(cut_list)) == 1:
                    saved_index.append(cut_list[0])
                else:
                    saved_index += self.get_out_k(question, topk_ctxs, cut_list)
        # step 2: aggregation
        if len(saved_index) < self.listwise_k: # agg, fill out missing and run final
            other_index = self.get_leftover_idx(saved_index, self.listwise_k - len(saved_index), full_list_idx)
            full_index = saved_index + other_index
            topk_out = self.get_out_k(question, topk_ctxs, full_index)
            return topk_out[-1]
        elif len(saved_index) > self.listwise_k:
            return self.run_one_loop(question, topk_ctxs, saved_index)
        elif len(saved_index) == 1:
            return saved_index[0]
        else:# length is exactly the same as listwise_k
            return self.get_out_k(question, topk_ctxs, saved_index)[-1]

    # 检查并修正列表中的无效项
    def check_valid_list(self, full_list):
        for exc in self.global_exclude:
            while exc in full_list:
                exc_idx = full_list.index(exc)
                new_val = (exc + 1) % len(full_list)
                while new_val in self.global_exclude:
                    new_val = (new_val + 1) % len(full_list)
                full_list[exc_idx] = new_val
        return full_list
    
    # 批量运行推理 并缓存结果
    def run_batchwise_caching(self, batch_holder):
        for iter_start in tqdm(range(0, self.topk, self.listwise_k)):
            iter_end = iter_start + self.listwise_k
            questions = [x['question'] for x in batch_holder]
            topk_ctxs = [x['topk_ctxs'][iter_start:iter_end] for x in batch_holder]
            # make batchwise input
            full_input_texts_batchwise = [self.make_listwise_text(q, c) for q,c in zip(questions, topk_ctxs)]
            if len(full_input_texts_batchwise[0]) != self.listwise_k:
                continue
            raw_tensors_batchwise = [self.tok(x,
                padding = self.padding,
                return_tensors='pt',
                max_length = self.max_input_length,
                truncation=True) for x in full_input_texts_batchwise]
            batch_inputids = torch.stack([x['input_ids'] for x in raw_tensors_batchwise]).to(self.device)
            batch_attnmasks = torch.stack([x['attention_mask'] for x in raw_tensors_batchwise]).to(self.device)
            #he = time.time()
            output = self.run_inference({'input_ids': batch_inputids, 'attention_mask': batch_attnmasks})
            #ho = time.time()
            #self.imsi.append(ho-he)
            #print(self.imsi)
            del batch_inputids
            del batch_attnmasks
            batch_best_rel_ids = [[x-1 for x in topk] for topk in self.get_rel_index(output)]
            cand_def_ids = tuple(range(iter_start, iter_end)) # we can assume that it's already sorted
            batch_best_def_ids = [[cand_def_ids[x] for x in y] for y in batch_best_rel_ids]
            # add result to cache
            for i in range(len(batch_holder)):
                batch_holder[i]['best_cache'][tuple(set(cand_def_ids))] = batch_best_def_ids[i]
        return batch_holder

    # 运行锦标赛排序排序
    def run_tournament_sort(self, query, documents):
        skip_idx = 0
        short_idx = 0
        normal_idx = 0
        cached_output = []    # 存储输出结果
        print(f"Running first batchwise iteration..")
        batch_holder = []     # 临时存储每个批次的数据

        question = query  # 使用 self.args.question_text_key 作为键来访问 instance 字典中的对应值
        topk_ctxs = [doc for doc in documents]  # 使用 self.args.topk_ctxs_key 作为键来访问 instance 字典中的对应值
        # topk_ctxs = [f"{doc.content}".strip() for doc in documents]

        # handling exceptions
        # (2) prepare for skipping those that don't have gold in topk(100)
        top100_goldidx = [i for i in range(self.topk)]               # 传输的数据肯定是相关的文档
        if len(top100_goldidx) == 0 and self.skip_no_candidate:  # 出现len=0是什么情况？
            if self.verbose:
                print('No gold in bm25 top100. skip this instance')
            cached_output.append({'i': 0, 'question': question, 'topk_ctxs': topk_ctxs, 'goldidx': [], 'best_cache': {}})
            skip_idx += 1
            # (3) don't batch calculate those that have shorter topk than topk(100)
            # 如果 topk_ctxs 的长度小于 self.args.topk，则将该实例直接添加到 cached_output 中
        elif len(topk_ctxs) < self.topk:
            cached_output.append({'i': 0, 'question': question, 'topk_ctxs': topk_ctxs, 'goldidx': top100_goldidx, 'best_cache': {}})
            short_idx += 1
        else: # 正常处理
            normal_idx += 1
            temp_instance = {'i': 0, 'question': question, 'topk_ctxs': topk_ctxs, 'goldidx': top100_goldidx, 'best_cache': {}}
            batch_holder.append(temp_instance)
            if (len(batch_holder) == self.bsize):
                output = self.run_batchwise_caching(batch_holder)   # 运行批量推理 run_batchwise_caching
                cached_output += output
                batch_holder = [] # reset batch holder variables

        # 剩余实例的处理
        if len(batch_holder) != 0:
            cached_output += self.run_batchwise_caching(batch_holder)
            batch_holder = []
        
        cached_output = sorted(cached_output, key=lambda x: x['i'])     # 按照原始顺序进行排序，其实可以不用

        # for instance, cache in tqdm(zip(self.test_file, cached_output), total=len(cached_output)):
        cache = cached_output[0]
        top100_goldidx = cache['goldidx']
        saved_topones = []
        self.global_exclude = []
        self.best_cache = cache['best_cache']
        topk_ctxs = cache['topk_ctxs']
        question = cache['question']

        if len(top100_goldidx) == 0 and self.skip_no_candidate:
            if self.verbose:
                print(f"No gold in candidate list. skipping.")
            # temp.append(instance)
        elif len(topk_ctxs) == 0:
            print(f"No topk_ctxs. Skipping reranking.")
            # temp.append(instance)
        elif len(topk_ctxs) == 1:
            if self.verbose:
                print(f"Length of topk ctxs is 1. Skipping reranking.")
            # temp.append(instance)
        else:
            full_list_idx = list(range(len(topk_ctxs)))
            if len(full_list_idx) <= self.listwise_k:
                print('get full order in one loop')
                saved_topones = self.get_full_order_in_one_loop(question, topk_ctxs, full_list_idx)
                print('get full order in one loop done')
            else:
                if len(full_list_idx) != len(cache['topk_ctxs']):
                    print("sth wrong!!!")
                    import pdb; pdb.set_trace()
                
                # 进行 rerank_top 次迭代   full_list_idx List[0...99] 100
                for topk_i in range(min(self.rerank_topk, len(full_list_idx))):
                    # 通过 run_one_loop 找到最相关的根元素
                    top1_def_idx = self.run_one_loop(question, topk_ctxs, full_list_idx)
                    top1_rel_idx = full_list_idx.index(top1_def_idx)
                    self.global_exclude.append(top1_def_idx)
                    
                    if (len(full_list_idx) <= self.rerank_topk) and (len(self.global_exclude) == len(full_list_idx)):
                        saved_topones.append(top1_def_idx)
                        break
                    if (self.out_k * 2) > self.listwise_k:
                            full_list_idx = full_list_idx[:top1_rel_idx] + full_list_idx[top1_rel_idx:]
                    else:   # 替代原本最相关文档的位置   dummy_number 只要大于5就行
                        full_list_idx[top1_rel_idx] = (top1_def_idx + self.dummy_number) % len(full_list_idx)
                    # 检查替代后列表索引的合理性
                    full_list_idx = self.check_valid_list(full_list_idx)
                    saved_topones.append(top1_def_idx)
                    if set(top100_goldidx).issubset(set(saved_topones)) and self.skip_issubset:
                        if self.verbose:
                            print(f'Subset reached for gold: {top100_goldidx}, pred: {saved_topones}. Skipping the rest')
                        break
            
            # 这里的saved_topones 就是所需要的 rerank_topk 的相关文档索引  [0...99] 的数字范围
            sorted_documents = []
            for i in saved_topones:
                sorted_documents.append(documents[i])

            return sorted_documents
        

    
    


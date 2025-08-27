import json
import re
from typing import List, Tuple
from tqdm import tqdm
import numpy as np
import json_repair
from vllm import LLM, SamplingParams
from vllm.lora.request import LoRARequest
from transformers import AutoTokenizer, AutoModelForSequenceClassification, AutoModel

from sage.libs.rag.longrefiner.longrefiner.prompt_template import PromptTemplate
from sage.libs.rag.longrefiner.longrefiner.task_instruction import *


class LongRefiner:
    def __init__(
        self,
        base_model_path: str = "Qwen/Qwen2.5-3B-Instruct",
        query_analysis_module_lora_path: str = "",
        doc_structuring_module_lora_path: str = "",
        global_selection_module_lora_path: str = "",
        score_model_name: str = "bge-reranker-v2-m3",
        score_model_path: str = "BAAI/bge-reranker-v2-m3",
        max_model_len: int = 25000,
        gpu_device: int = 0,
    ):
        # load refine model
        self._load_trained_model(
            base_model_path,
            query_analysis_module_lora_path,
            doc_structuring_module_lora_path,
            global_selection_module_lora_path,
            max_model_len,
            gpu_device,
        )
        self._load_score_model(score_model_name, score_model_path, gpu_device)

    def _load_trained_model(
        self,
        base_model_path: str,
        query_analysis_module_lora_path: str,
        doc_structuring_module_lora_path: str,
        global_selection_module_lora_path: str,
        max_model_len: int = 25000,
        gpu_device: int = 0,
    ):
        import os
        # 设置 CUDA_VISIBLE_DEVICES 环境变量来指定GPU
        os.environ["CUDA_VISIBLE_DEVICES"] = str(gpu_device)
        
        self.model = LLM(
            base_model_path, 
            enable_lora=True, 
            max_model_len=max_model_len, 
            gpu_memory_utilization=0.7,
            tensor_parallel_size=1  # 单GPU设置
        )
        self.tokenizer = AutoTokenizer.from_pretrained(base_model_path)
        self.step_to_config = {
            "query_analysis": {
                "lora_path": query_analysis_module_lora_path,
                "lora_request": LoRARequest(
                    lora_name="query_analysis", lora_int_id=1, lora_path=query_analysis_module_lora_path
                ),
                "sampling_params": SamplingParams(temperature=0, max_tokens=2, logprobs=20),
                "prompt_template": PromptTemplate(
                    self.tokenizer, system_prompt=SYSTEM_PROMPT_STEP1, user_prompt=USER_PROMPT_STEP1
                ),
            },
            "doc_structuring": {
                "lora_path": doc_structuring_module_lora_path,
                "lora_request": LoRARequest(
                    lora_name="doc_structuring", lora_int_id=2, lora_path=doc_structuring_module_lora_path
                ),
                "sampling_params": SamplingParams(temperature=0, max_tokens=10000),
                "prompt_template": PromptTemplate(
                    self.tokenizer, system_prompt=SYSTEM_PROMPT_STEP2, user_prompt=USER_PROMPT_STEP2
                ),
            },
            "global_selection": {
                "lora_path": global_selection_module_lora_path,
                "lora_request": LoRARequest(
                    lora_name="global_selection", lora_int_id=3, lora_path=global_selection_module_lora_path
                ),
                "sampling_params": SamplingParams(temperature=0, max_tokens=10000),
                "prompt_template": PromptTemplate(
                    self.tokenizer, system_prompt=SYSTEM_PROMPT_STEP3, user_prompt=USER_PROMPT_STEP3
                ),
            },
        }

    def _cal_score_bm25(self, all_pairs: List[Tuple[str, str]]) -> List[float]:
        from rank_bm25 import BM25Okapi
        from collections import OrderedDict

        corpus_dict = OrderedDict()
        for pair in all_pairs:
            question = pair[0]
            doc = pair[1]
            if question not in corpus_dict:
                corpus_dict[question] = []
            corpus_dict[question].append(doc)
        for q in corpus_dict.keys():
            corpus_dict[q] = [d.split(" ") for d in corpus_dict[q]]
            corpus_dict[q] = BM25Okapi(corpus_dict[q])
            corpus_dict[q] = corpus_dict[q].get_scores(q.split(" ")).tolist()
        all_scores = []
        for q, s in corpus_dict.items():
            all_scores.extend(s)
        return all_scores

    def _cal_score_reranker(self, all_pairs: List[Tuple[str, str]]) -> List[float]:
        import torch

        all_scores = []
        batch_size = 256
        for idx in tqdm(range(0, len(all_pairs), batch_size)):
            batch_pairs = all_pairs[idx : idx + batch_size]
            with torch.no_grad():
                inputs = self.score_tokenizer(
                    batch_pairs, padding=True, truncation=True, return_tensors="pt", max_length=512
                )
                inputs = {k: v.cuda() for k, v in inputs.items()}
                if "bce" in self.score_model_name or "jina" in self.score_model_name:
                    flatten_scores = (
                        self.score_model(**inputs, return_dict=True)
                        .logits.view(
                            -1,
                        )
                        .float()
                    )
                    flatten_scores = torch.sigmoid(flatten_scores).tolist()
                else:
                    flatten_scores = (
                        self.score_model(**inputs, return_dict=True)
                        .logits.view(
                            -1,
                        )
                        .float()
                        .tolist()
                    )
                all_scores.extend(flatten_scores)
        return all_scores

    def _cal_score_sbert(self, all_pairs: List[Tuple[str, str]]) -> List[float]:
        def pooling(pooler_output, last_hidden_state, attention_mask=None, pooling_method="mean"):
            if pooling_method == "mean":
                last_hidden = last_hidden_state.masked_fill(~attention_mask[..., None].bool(), 0.0)
                return last_hidden.sum(dim=1) / attention_mask.sum(dim=1)[..., None]
            elif pooling_method == "cls":
                return last_hidden_state[:, 0]
            elif pooling_method == "pooler":
                return pooler_output
            else:
                raise NotImplementedError("Pooling method not implemented!")

        import torch

        batch_size = 512
        all_scores = []
        for idx in tqdm(range(0, len(all_pairs), batch_size)):
            batch_pairs = all_pairs[idx : idx + batch_size]
            with torch.no_grad():
                if "e5" in self.score_model_name:
                    q_list = [f"query: {p[0]}" for p in batch_pairs]
                    d_list = [f"passage: {p[1]}" for p in batch_pairs]
                else:
                    q_list = [p[0] for p in batch_pairs]
                    d_list = [p[1] for p in batch_pairs]

                inputs = self.score_tokenizer(
                    q_list, max_length=256, padding=True, truncation=True, return_tensors="pt"
                )
                inputs = {k: v.cuda() for k, v in inputs.items()}
                output = self.score_model(**inputs, return_dict=True)
                q_emb = pooling(output.pooler_output, output.last_hidden_state, inputs["attention_mask"], "mean")
                q_emb = torch.nn.functional.normalize(q_emb, dim=-1)
                inputs = self.score_tokenizer(
                    d_list, max_length=512, padding=True, truncation=True, return_tensors="pt"
                )
                inputs = {k: v.cuda() for k, v in inputs.items()}
                output = self.score_model(**inputs, return_dict=True)
                d_emb = pooling(output.pooler_output, output.last_hidden_state, inputs["attention_mask"], "mean")
                d_emb = torch.nn.functional.normalize(d_emb, dim=-1)
                score_list = q_emb @ d_emb.T
                score_list = torch.diag(score_list).detach().cpu().tolist()
                all_scores.extend(score_list)
        return all_scores

    def _load_score_model(self, score_model_name: str, score_model_path: str):
        self.score_model_name = score_model_name
        if score_model_name == "bm25":
            self.score_model = None
            self.score_tokenizer = None
            self.local_score_func = self._cal_score_bm25
            return
        elif "reranker" in score_model_name:
            self.score_model = AutoModelForSequenceClassification.from_pretrained(score_model_path)
            self.score_tokenizer = AutoTokenizer.from_pretrained(score_model_path, use_fast=False)
            self.local_score_func = self._cal_score_reranker
        else:
            self.score_model = AutoModel.from_pretrained(score_model_path)
            self.score_tokenizer = AutoTokenizer.from_pretrained(score_model_path, use_fast=False)
            self.local_score_func = self._cal_score_sbert
        
        # 指定GPU设备
        if hasattr(self, 'gpu_device') and self.gpu_device is not None:
            device = f"cuda:{self.gpu_device}"
            self.score_model.to(device)
        else:
            self.score_model.cuda()
        self.score_model.eval()
        self.score_model.half()

    def run(
        self,
        question: str,
        document_list: List[dict],
        budget: int = 2048,
        ratio: float = None,
    ) -> List[str]:
        return self.batch_run([question], [document_list], budget, ratio)[0]

    def batch_run(
        self,
        question_list: List[str],
        document_list: List[List[dict]],
        budget: int = 2048,
        ratio: float = None,
    ) -> List[List[str]]:
        """
        Args:
            question_list: List[str], each question is a string
            document_list: List[List[dict]], each item is a list of documents, each document is a dictionary, contains 'content': "{title}\n{content}"
            budget: int, the final token budget for the refine model
            ratio: float, the ratio of the token budget for the score model (only used when ratio is not None, and the priority of `budget` is higher)

        Output:
            List[str], each string is a refiner output of the document in document_list
        """

        # step1: query analysis
        query_analysis_result = self.run_query_analysis(question_list)

        # step2: doc structuring
        doc_structuring_result = self.run_doc_structuring(document_list)

        # step3: context selection (local + global)
        # refined_content_list: List[str]: each string is the refined content of the question
        refined_content_list = self.run_all_search(
            question_list=question_list,
            document_list=document_list,
            query_analysis_result=query_analysis_result,
            doc_structuring_result=doc_structuring_result,
            budget=budget,
            ratio=ratio,
        )

        return refined_content_list

    def run_query_analysis(self, question_list: List[str]) -> List[dict]:
        """
        Args:
            question_list: List[str], each question is a string
        Output:
            List[dict], each dict contains the local and global information of the question
        """
        # get special token id
        special_token = ["Local", "Global"]
        id2special = {self.tokenizer.encode(token)[0]: token for token in special_token}
        # get prompt template, sampling params, lora request
        prompt_template = self.step_to_config["query_analysis"]["prompt_template"]
        sampling_params = self.step_to_config["query_analysis"]["sampling_params"]
        lora_request = self.step_to_config["query_analysis"]["lora_request"]

        prompt_list = [prompt_template.get_prompt(question=question) for question in question_list]
        output_list = self.model.generate(prompt_list, sampling_params=sampling_params, lora_request=lora_request)

        query_analysis_result = []
        for output in output_list:
            # set init prob for special token
            special_token_prob = {token: -100 for token in special_token}
            logprobs = output.outputs[0].logprobs[1]
            for token_id, logprob in logprobs.items():
                if token_id in id2special:
                    special_token_prob[id2special[token_id]] = logprob.logprob
            for k, v in special_token_prob.items():
                special_token_prob[k] = np.exp(v)
            query_analysis_result.append(special_token_prob)
        return query_analysis_result

    def run_doc_structuring(self, document_list: List[List[dict]]) -> List[List[dict]]:
        """
        Args:
            document_list: List[List[dict]], each item is a list of documents, each document is a dictionary, contains a key 'content': "{title}\n{content}"
        Output:
            List[List[dict]], each item is a list of documents, each document is a dictionary, contains the structured content of the document
        """
        # get prompt template, sampling params, lora request
        prompt_template = self.step_to_config["doc_structuring"]["prompt_template"]
        sampling_params = self.step_to_config["doc_structuring"]["sampling_params"]
        lora_request = self.step_to_config["doc_structuring"]["lora_request"]

        # get doc content (doc title is not used)
        doc_content_list = [
            ["\n".join(doc["contents"].split("\n")[1:]) for doc in item_doc_list] for item_doc_list in document_list
        ]
        # truncate doc content if it is too long
        doc_content_list = [
            [self._truncate_doc_content(doc_content) for doc_content in item_doc_content_list]
            for item_doc_content_list in doc_content_list
        ]

        # for each doc, get the input prompt and output the structured content
        prompt_list = sum(
            [
                [prompt_template.get_prompt(doc_content=doc_content) for doc_content in zip(item_doc_content_list)]
                for item_doc_content_list in doc_content_list
            ],
            [],
        )
        output_list = self.model.generate(prompt_list, sampling_params=sampling_params, lora_request=lora_request)

        # parse output to structured content
        structured_doc_list = []
        start_idx = 0
        for idx, item_doc_list in enumerate(doc_content_list):
            item_structured_docs = []
            for doc_idx, doc_content in enumerate(item_doc_list):
                output = output_list[start_idx]
                doc_title = document_list[idx][doc_idx]["contents"].split("\n")[0]
                structured_doc = self.parse_xml_doc(doc_content, output.outputs[0].text)
                structured_doc["title"] = doc_title
                item_structured_docs.append(structured_doc)
                start_idx += 1
            structured_doc_list.append(item_structured_docs)

        return structured_doc_list

    def run_global_selection(self, question_list: List[str], structured_doc_list: List[List[dict]]) -> List[List[dict]]:
        """
        Args:
            question_list: List[str], each question is a string
            structured_doc_list: List[List[dict]], each item is a list of documents, each document is a dictionary, contains the structured content of the document
        Output:
            List[List[dict]], each item is a list of documents, each document is a dictionary, contains the selected content of the document
        """
        # get prompt template, sampling params, lora request
        prompt_template = self.step_to_config["global_selection"]["prompt_template"]
        sampling_params = self.step_to_config["global_selection"]["sampling_params"]
        lora_request = self.step_to_config["global_selection"]["lora_request"]

        prompt_list = []
        for question, item_doc_list in zip(question_list, structured_doc_list):
            for doc in item_doc_list:
                abstract = doc.get("abstract", "")
                if abstract is None:
                    abstract = ""
                elif isinstance(abstract, list):
                    abstract = "\n".join(abstract)
                title = doc["title"]
                outline = f"Title: {title}\n"

                sections = doc["sections"]
                section_idx = 1
                for section_title, section_dict in sections.items():
                    subsection_idx = 1
                    if section_dict["content"] is not None or section_dict["subsections"] != {}:
                        outline += f"Section{section_idx}: {section_title}\n"
                        section_idx += 1
                    if section_dict["subsections"] != {}:
                        for subsection, subsection_content in section_dict["subsections"].items():
                            outline += f"Subsection{subsection_idx}: {subsection}\n"
                            subsection_idx += 1

                prompt = prompt_template.get_prompt(question=question, abstract=abstract, outline=outline)
                prompt_list.append(prompt)

        output_list = self.model.generate(prompt_list, sampling_params=sampling_params, lora_request=lora_request)
        global_selection_result = []
        idx = 0
        for question, item_doc_list in zip(question_list, structured_doc_list):
            item_global_selection_result = []
            for doc in item_doc_list:
                selected_title = output_list[idx].outputs[0].text
                selected_title = json_repair.loads(selected_title)
                if isinstance(selected_title, dict):
                    selected_title = selected_title.get("selected_titles", [])
                elif len(selected_title) > 1 and isinstance(selected_title[0], dict):
                    selected_title = selected_title[0].get("selected_titles", [])
                selected_title = [i.lower() for i in selected_title]

                item_global_selection_result.append(selected_title)
                idx += 1
            global_selection_result.append(item_global_selection_result)
        return global_selection_result

    def _truncate_doc_content(self, doc_content: str, max_length: int = 25000) -> str:
        """
        Args:
            doc_content: str, the content of the document
            max_length: int, the max length of the document
        Output:
            str, the truncated document content
        """
        tokenized_content = self.tokenizer(doc_content, truncation=False, return_tensors="pt").input_ids[0]
        half = max_length // 2
        # truncate the middle content
        if len(tokenized_content) > max_length:
            doc_content = self.tokenizer.decode(
                tokenized_content[:half], skip_special_tokens=True
            ) + self.tokenizer.decode(tokenized_content[-half:], skip_special_tokens=True)
        return doc_content

    def _fill_single_sequence(self, content: str, part_sequence: str) -> str:
        # generate regex pattern for part_sequence
        if "..." in part_sequence:
            first_part, last_part = part_sequence.split("...")[0], part_sequence.split("...")[1]
            first_part = " ".join(first_part.split(" ")[:4])
            last_part = " ".join(last_part.split(" ")[-4:])
            part_sequence = first_part + "..." + last_part
        escaped_sentence = re.escape(part_sequence)
        escaped_sentence = escaped_sentence.replace(r"\(\)", r"\(.*?\)")
        escaped_sentence = escaped_sentence.replace(r"\.\.\.", r".*?")
        pattern = rf"({escaped_sentence})"

        # fill the full content
        full_content = re.findall(pattern, content)
        if full_content == []:
            return None
        else:
            return full_content[-1]

    def _fill_full_content(self, content: str, part_content: str) -> str:
        """
        Fill in placeholders in part_comtent. Fill in according to split paragraphs.

        Args:
            content: str, the original content
            part_content: str, the part content to be filled
        Output:
            str, the filled content
        """

        def cut(s, sub_s):
            index = s.find(sub_s)
            if index != -1:
                result = s[index + len(sub_s) :]
            else:
                result = s
            return result

        if "<br>" in part_content:
            part_sequences = part_content.split("<br>")
        else:
            part_sequences = part_content.split("\n")
        part_sequences = [s.strip() for s in part_sequences if s != ""]
        total_content = []
        temp_content = content
        for part_sequence in part_sequences:
            full_content = self._fill_single_sequence(temp_content, part_sequence)
            if full_content is not None:
                total_content.append(full_content)
                temp_content = cut(temp_content, full_content)
        if total_content == []:
            return None
        else:
            return "\n".join(total_content)

    def _get_paragraphs(self, text: str) -> List[str]:
        """
        Args:
            text: str, the text to be split into paragraphs
        Output:
            List[str], the paragraphs of the text
        """
        chunks = text.split("\n")
        chunks = [i for i in chunks if i != ""]
        new_chunks = []
        exist_str = ""
        for chunk in chunks:
            if exist_str != "":
                chunk = exist_str + " " + chunk
            if len(chunk.split(" ")) < 100:
                exist_str = chunk
                continue
            else:
                exist_str = ""
                new_chunks.append(chunk)
        if exist_str != "":
            new_chunks.append(exist_str)
        if not isinstance(new_chunks, list):
            assert False
        return new_chunks

    def parse_xml_doc(self, original_doc_content: str, xml_doc: str) -> dict:
        """
        Args:
            original_doc_content: str, the original document content
            output_text: str, the output text of the model
        Output:
            dict, the structured content of the document
        """

        pattern = r"<abstract>(.*?)</abstract>|<section: (.*?)>(.*?)</section: \2>"
        sub_section_pattern = r'<sub-section: "([^"]+)">(.*?)</sub-section: "\1">'
        matches = re.findall(pattern, xml_doc, re.DOTALL)

        structured_doc = {"abstract": None, "sections": {}}

        for match in matches:
            if match[0]:  # find abstract content
                structured_doc["abstract"] = match[0].strip()
            else:
                section_name = match[1].strip()
                section_content = match[2].strip()
                subsections = re.findall(sub_section_pattern, section_content, re.DOTALL)
                structured_doc["sections"][section_name] = {
                    "content": re.sub(sub_section_pattern, "", section_content, flags=re.DOTALL).strip(),
                    "subsections": {sub[0].strip(): sub[1].strip() for sub in subsections},
                }

        # fill the middle content of sections and subsections
        if "abstract" in structured_doc and structured_doc["abstract"] != None:
            structured_doc["abstract"] = self._fill_full_content(original_doc_content, structured_doc["abstract"])
        sections = structured_doc["sections"]
        for section_title, section_dict in sections.items():
            if section_dict["content"] != "":
                section_dict["content"] = self._fill_full_content(original_doc_content, section_dict["content"])
            subsection_dict = section_dict["subsections"]
            for subsection_title, subsection_content in subsection_dict.items():
                subsection_dict[subsection_title] = self._fill_full_content(original_doc_content, subsection_content)

        # fill in the abstract
        if "abstract" in structured_doc and structured_doc["abstract"] is None:
            abs = None
            for section, section_item in structured_doc["sections"].items():
                if section_item["content"] is not None and section_item["content"] != "":
                    abs = original_doc_content.split(section_item["content"])[0]
                    structured_doc["abstract"] = abs
                    break
                if section_item["subsections"] != {}:
                    for subsection, subsection_content in section_item["subsections"].items():
                        if subsection_content != None and subsection_content != "":
                            abs = original_doc_content.split(subsection_content)[0]
                            structured_doc["abstract"] = abs
                            break
        # clean result
        if "abstract" in structured_doc:
            if structured_doc["abstract"] is None or structured_doc["abstract"] == "":
                pass
            else:
                structured_doc["abstract"] = self._get_paragraphs(structured_doc["abstract"])
        sections = structured_doc["sections"]
        for section_title, section_dict in list(sections.items()):
            if section_dict["content"] == "" or section_dict["content"] is None:
                if section_dict["subsections"] == {} or set(list(section_dict["subsections"].values())) == {""}:
                    del sections[section_title]
                else:
                    section_dict["content"] = []
            else:
                section_dict["content"] = self._get_paragraphs(section_dict["content"])
                if section_dict["subsections"] != {} and set(list(section_dict["subsections"].values())) != {""}:
                    for subsection, subsection_content in list(section_dict["subsections"].items()):
                        if subsection_content == "" or subsection_content is None:
                            del section_dict["subsections"][subsection]
                        else:
                            section_dict["subsections"][subsection] = self._get_paragraphs(subsection_content)
        return structured_doc

    def _collect_hierarchical_nodes(
        self,
        question_list: List[str],
        doc_structuring_result: List[List[dict]],
    ) -> List[dict]:
        """
        Collect all hierarchical nodes, each represents a paragraph
        """
        all_nodes = []
        for idx, (question, structuring_doc_list) in enumerate(zip(question_list, doc_structuring_result)):
            for doc_idx, doc in enumerate(structuring_doc_list):
                if "abstract" in doc:
                    if doc["abstract"] is None or doc["abstract"] == "" or doc["abstract"] == []:
                        pass
                    else:
                        for chunk in doc["abstract"]:
                            all_nodes.append(
                                {
                                    "idx": idx,
                                    "question": question,
                                    "doc_idx": doc_idx,
                                    "type": "paragraph",
                                "parent": "abstract",
                                "parent_type": "abstract",
                                "content": chunk,
                                }
                            )

                sections = doc["sections"]
                for section_title, section_dict in list(sections.items()):
                    if section_dict["content"] == [] or section_dict["content"] is None:
                        if section_dict["subsections"] == {} or set(list(section_dict["subsections"].values())) == {""}:
                            del sections[section_title]
                    else:
                        assert isinstance(section_dict["content"], list), section_dict["content"]
                        for chunk in section_dict["content"]:
                            all_nodes.append(
                                {
                                    "idx": idx,
                                    "question": question,
                                    "doc_idx": doc_idx,
                                    "type": "paragraph",
                                    "parent": section_title,
                                    "parent_type": "section",
                                    "content": chunk,
                                }
                            )
                        if section_dict["subsections"] != {}:
                            for subsection, subsection_content in list(section_dict["subsections"].items()):
                                if subsection_content == "" or subsection_content == None:
                                    del section_dict["subsections"][subsection]
                                else:
                                    assert isinstance(subsection_content, list)
                                    for chunk in subsection_content:
                                        all_nodes.append(
                                            {
                                                "idx": idx,
                                                "question": question,
                                                "doc_idx": doc_idx,
                                                "type": "paragraph",
                                                "parent": subsection,
                                                "parent_type": "subsection",
                                                "grandparent": section_title,
                                                "content": chunk,
                                            }
                                        )
        return all_nodes

    def run_all_search(
        self,
        question_list: List[str],
        document_list: List[List[dict]],
        doc_structuring_result: List[List[dict]],
        query_analysis_result: List[dict],
        budget: int,
        ratio: float = None,
    ) -> List[str]:
        """
        Args:
            question_list: List[str], each question is a string
            document_list: List[dict], each item is a document, each document is a dictionary, contains the original content of the document
            doc_structuring_result: List[List[dict]], each item is a list of documents, each document is a dictionary, contains the structured content of the document
            query_analysis_result: List[dict], each dict contains the local and global information of the question
            budget: int, the final token budget for the refine model
            ratio: float, the ratio of the token budget for the score model (only used when ratio is not None, and the priority of `budget` is higher)
        Output:
            List[str], each string is a refiner output of the document in document_list
        """
        # collect hierarchical nodes
        # print(doc_structuring_result[0][0])
        # assert False
        all_nodes = self._collect_hierarchical_nodes(question_list, doc_structuring_result)

        # calculate local score
        node_pairs = [(node["question"], node["content"]) for node in all_nodes]
        node_scores = self.local_score_func(node_pairs)
        for node, score in zip(all_nodes, node_scores):
            node["score"] = score

        # transmit similarity to parent node
        idx2node = {}
        parent2node = {}
        for node in all_nodes:
            idx = node["idx"]
            parent = f'{node["question"]}_{node["doc_idx"]}_{node["parent"]}'
            if idx not in idx2node:
                idx2node[idx] = []
            if parent not in parent2node:
                parent2node[parent] = []
            idx2node[idx].append(node)
            parent2node[parent].append(node)

        for idx, node_list in idx2node.items():
            question = node_list[0]["question"]
            # get corresponding structured_doc_list
            for doc_idx, doc in enumerate(doc_structuring_result[idx]):
                if "abstract" in doc:
                    if doc["abstract"] is None or doc["abstract"] == "":
                        pass
                    else:
                        parent = f"{question}_{doc_idx}_abstract"
                        score_list = [node["score"] for node in parent2node[parent]]
                        score = sum(score_list) / len(score_list)
                        node_list.append(
                            {
                                "idx": idx,
                                "question": question,
                                "doc_idx": doc_idx,
                                "type": "abstract",
                                "parent": "root",
                                "parent_type": "root",
                                "title": "abstract",
                                "score": score,
                            }
                        )

                sections = doc["sections"]
                for section_title, section_dict in list(sections.items()):
                    if section_dict["content"] == [] or section_dict["content"] is None:
                        if section_dict["subsections"] == {} or set(list(section_dict["subsections"].values())) == {""}:
                            del sections[section_title]
                    else:
                        parent = f"{question}_{doc_idx}_{section_title}"
                        if parent in parent2node:
                            score_list = [node["score"] for node in parent2node[parent]]
                            if len(score_list) != 0:
                                score_list = [sum(score_list) / len(score_list)]
                            else:
                                score_list = []
                        else:
                            score_list = []

                        if section_dict["subsections"] != {}:
                            for subsection, subsection_content in list(section_dict["subsections"].items()):
                                if subsection_content == "":
                                    del section_dict["subsections"][subsection]
                                else:
                                    parent = f"{question}_{doc_idx}_{subsection}"
                                    sub_score_list = [node["score"] for node in parent2node[parent]]
                                    sub_score = sum(sub_score_list) / len(sub_score_list)
                                    score_list.append(sub_score)
                                    node_list.append(
                                        {
                                            "idx": idx,
                                            "question": question,
                                            "doc_idx": doc_idx,
                                            "type": "subsection",
                                            "parent": section_title,
                                            "parent_type": "section",
                                            "title": subsection,
                                            "score": sub_score,
                                        }
                                    )
                    if score_list != []:
                        score = sum(score_list) / len(score_list)
                    else:
                        score = 0
                    node_list.append(
                        {
                            "idx": idx,
                            "question": question,
                            "doc_idx": doc_idx,
                            "type": "section",
                            "parent": "root",
                            "parent_type": "root",
                            "title": section_title,
                            "score": score,
                        }
                    )

        # min-max normalization
        for idx, node_list in idx2node.items():
            score_list = [i["score"] for i in node_list]
            min_score, max_score = min(score_list), max(score_list)
            for node in node_list:
                if max_score == min_score:
                    node["score"] = 0
                else:
                    node["score"] = (node["score"] - min_score) / (max_score - min_score)

        # combine global score
        global_selection_result = self.run_global_selection(question_list, doc_structuring_result)
        for idx, node_list in idx2node.items():
            for node in node_list:
                question = question_list[idx]
                query_scores = query_analysis_result[idx]
                global_ratio = query_scores["Global"]
                local_ratio = query_scores["Local"]
                alpha = global_ratio / (global_ratio + local_ratio)

                selected_title_list = global_selection_result[idx][node["doc_idx"]]

                if node.get("title", "").lower() in selected_title_list:
                    node["score"] += alpha
                if node["parent"].lower() in selected_title_list:
                    # calculate the number of leaf nodes
                    parent_type = node["parent_type"]
                    if parent_type == "section":
                        parent_dict = doc_structuring_result[idx][node['doc_idx']]['sections'][node["parent"]]
                        leaf_num = len(parent_dict.get("subsections", {}))
                    elif parent_type == "subsection":
                        leaf_num = len(
                            doc_structuring_result[idx][node['doc_idx']]['sections'][node["grandparent"]]["subsections"][node["parent"]]
                        )
                    else:
                        continue
                    node["score"] += alpha / (leaf_num + 1)

        # select by budget(ratio)
        refined_node_list = self.select_by_budget(
            question_list, doc_structuring_result, all_nodes, idx2node, budget, ratio
        )
        for item_node_list in refined_node_list:
            for node in item_node_list:
                print(node)
                print("-----")
                
        final_contents_list = [[node["contents"] for node in item_node_list] for item_node_list in refined_node_list]
        return final_contents_list

    def select_by_budget(
        self,
        question_list: List[str],
        structured_document_list: List[List[dict]],
        all_nodes: List[dict],
        idx2node: dict,
        budget: int,
        ratio: float,
    ) -> List[List[dict]]:
        # process budget and ratio
        if budget is None:
            assert (
                ratio is not None and ratio > 0 and ratio < 1
            ), "budget is None, ratio must be a float between 0 and 1"
            idx2budget = {}
            for idx in idx2node:
                item_documents = document_list[idx]
                doc_contents = " ".join([doc["contents"] for doc in item_documents])
                doc_length = len(self.tokenizer(doc_contents)["input_ids"])
                budget = int(doc_length * ratio)
                idx2budget[idx] = budget
        else:
            idx2budget = {idx: budget for idx in idx2node}

        # final selection
        result_nodes = []
        for idx, node_list in tqdm(idx2node.items()):
            # use a large budget for pre selection
            budget = idx2budget[idx] * 2
            question = question_list[idx]
            cand_node_list = []
            sort_node_list = sorted(node_list, key=lambda x: x["score"], reverse=True)
            for node in sort_node_list:
                corr_doc_title = structured_document_list[idx][node["doc_idx"]]["title"]
                if node["type"] == "paragraph":
                    node_content = corr_doc_title + "\n" + node["content"]
                elif node["type"] == "abstract":
                    abstract = structured_document_list[idx][node["doc_idx"]]["abstract"]
                    if isinstance(abstract, list):
                        node_content = "\n".join(abstract)
                    else:
                        node_content = abstract
                    node_content = corr_doc_title + "\n" + node_content
                elif node["type"] == "section":
                    section_dict = structured_document_list[idx][node["doc_idx"]]["sections"][node["title"]]
                    node_content = f"{corr_doc_title}\n"
                    if section_dict["content"] == "" or section_dict["content"] is None:
                        pass
                    else:
                        if isinstance(section_dict["content"], list):
                            chunk_content += "\n".join(section_dict["content"])
                        else:
                            node_content = section_dict["content"]
                        node_content += "\n"
                    if section_dict["subsections"] != {}:
                        sub_idx = 1
                        for subsection, subsection_content in section_dict["subsections"].items():
                            if subsection_content != "":
                                chunk_content += f"Subsection {sub_idx}: {subsection}: \n{subsection_content}"
                                sub_idx += 1
                elif node["type"] == "subsection":
                    section_title = node["parent"]
                    subsection_title = node["title"]
                    node_content = structured_document_list[idx][node["doc_idx"]]["sections"][section_title][
                        "subsections"
                    ][subsection_title]
                    if isinstance(node_content, list):
                        node_content = "\n".join(node_content)
                else:
                    assert False
                assert isinstance(node_content, str), node_content
                node_length = len(self.tokenizer(node_content)["input_ids"])
                node["contents"] = node_content
                node["length"] = node_length
                if node_length > budget:
                    break
                else:
                    cand_node_list.append(node)
                    budget = budget - node_length

            budget = idx2budget[idx]
            final_node_list = []
            for idx, node in enumerate(cand_node_list):
                if budget < 0:
                    break
                # get other content under the same document
                exist_nodes = [
                    (c_idx, c)
                    for c_idx, c in enumerate(final_node_list)
                    if c["idx"] == node["idx"] and c["doc_idx"] == node["doc_idx"]
                ]

                if node["type"] == "paragraph":
                    # if exist parent node, skip current node
                    parent_nodes = [cc for cc in exist_nodes if cc[1].get("title", None) == node["parent"]]
                    if len(parent_nodes) > 0:
                        continue
                    else:
                        final_node_list.append(node)
                        budget = budget - node["length"]
                elif node["type"] == "abstract":
                    # search child node, if exist, keep current node
                    child_nodes = [cc for cc in exist_nodes if cc[1]["parent"] == "abstract"]

                    if len(child_nodes) > 0:
                        if budget + sum([cc[1]["length"] for cc in child_nodes]) < node["length"]:
                            continue
                        del_idx = []
                        for cc in child_nodes:
                            child_node_idx = cc[0]
                            child_node_length = cc[1]["length"]
                            del_idx.append(child_node_idx)
                            budget += child_node_length
                        final_node_list = [y for x, y in enumerate(final_node_list) if x not in del_idx]
                        final_node_list.append(node)
                        budget = budget - node["length"]
                    else:
                        final_node_list.append(node)
                        budget = budget - node["length"]
                else:
                    # for section or subsection
                    child_nodes = [cc for cc in exist_nodes if cc[1]["parent"] == node["title"]]
                    if len(child_nodes) > 0:
                        if budget + sum([cc[1]["length"] for cc in child_nodes]) < node["length"]:
                            continue
                        del_idx = []
                        for cc in child_nodes:
                            child_node_idx = cc[0]
                            child_node_length = cc[1]["length"]
                            del_idx.append(child_node_idx)
                            budget += child_node_length
                        final_node_list = [y for x, y in enumerate(final_node_list) if x not in del_idx]
                        final_node_list.append(node)
                        budget = budget - node["length"]
                    else:
                        final_node_list.append(node)
                        budget = budget - node["length"]

            result_nodes.append(final_node_list[:-1])
        return result_nodes
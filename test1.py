
# from src.core.embedding import embedding_modelpython -m src.core.embedding.embedding_model
# async def _test():
#     # huggingface example
#     embedding_model = EmbeddingModel("hf", model_name="sentence-transformers/all-MiniLM-L6-v2")
#     print(await embedding_model.embed(["123"]))

#     # mistralai example "mistral-embed"
#     embedding_model2 = EmbeddingModel("openai", model="mistral-embed", base_url="https://api.mistral.ai/v1",
#                                       api_key=os.environ.get("MISTRAL_API_KEY"))
#     print(await embedding_model2.embed(["123"]))

#     # cohere example
#     print(os.environ.get("COHERE_API_KEY"))
#     embedding_model3 = EmbeddingModel("cohere", model="embed-multilingual-v3.0",
#                                       api_key=os.environ.get("COHERE_API_KEY"))
#     print(await embedding_model3.embed(["123"]))

#     # jina example
#     embedding_model4 = EmbeddingModel("jina", api_key=os.environ.get('JINA_API_KEY'))
#     print(await embedding_model4.embed(["123"]))

#     # siliconcloud example
#     api_key = os.environ.get("SILICONCLOUD_API_KEY")
#     # print(api_key)
#     embedding_model5 = EmbeddingModel("openai", model="BAAI/bge-m3", base_url="https://api.siliconflow.cn/v1",
#                                       api_key=api_key)
#     print(await embedding_model5.embed(["123"]))


# if __name__ == "__main__":
#     asyncio.run(_test())


import re
import string
re_art = re.compile(r'\b(a|an|the)\b')
re_punc = re.compile(r'[!"#$%&()*+,-./:;<=>?@\[\]\\^`{|}~_\']')
def normalize_answer(s):
    """
    Lower text and remove punctuation, articles and extra whitespace.
    """
    s = s.lower()
    s = re_punc.sub(' ', s)
    s = re_art.sub(' ', s)
    s = ' '.join(s.split())
    return s
from collections import Counter
answer="Yes; Uphold, and continue."
prediction="yes"
answer = [answer]
answer_tokenized = [normalize_answer(ref).split() for ref in answer]
prediction_tokenized = normalize_answer(prediction).split()

print(answer_tokenized)
print(prediction_tokenized)

ref_tokenized = answer_tokenized[0]
common = Counter(prediction_tokenized) & Counter(ref_tokenized)
num_same = sum(common.values())
if sum(common.values()) == 0:
    f1 = 0
else:
    precision = 1.0 * num_same / len(prediction_tokenized)
    recall = 1.0 * num_same / len(ref_tokenized)
    f1 = 2 * precision * recall / (precision + recall)


print(f1)
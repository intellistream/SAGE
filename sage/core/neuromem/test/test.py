# python -m sage.core.neuromem.operator_test.operator_test

import bm25s
docs = [
    "The quick brown fox jumps over the lazy dog.",
    "Hello world! This is a operator_test document.",
    "Python is a great programming language."
]
tokenizer = bm25s.tokenization.Tokenizer(stopwords='en')
tokens = tokenizer.tokenize(docs)
bm25 = bm25s.BM25(corpus=docs, backend='numba')
bm25.index(tokens)

query = "python"
query_token = tokenizer.tokenize([query])[0]
scores = bm25.get_scores(query_token)
print('Scores:', scores)

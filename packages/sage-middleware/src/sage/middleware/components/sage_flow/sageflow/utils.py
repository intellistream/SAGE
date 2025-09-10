"""
Utils for SAGE Flow Python interface.
"""

from sageflow import MultiModalMessage, DataStream, IndexFunction

def create_text_message(uid, text):
    return MultiModalMessage(uid, "text", text)

def create_vector_message(uid, embeddings):
    return MultiModalMessage(uid, "vector", embeddings)

def from_list(data):
    return DataStream.from_list([create_text_message(i, str(d)) for i, d in enumerate(data)])

def create_index():
    return IndexFunction()
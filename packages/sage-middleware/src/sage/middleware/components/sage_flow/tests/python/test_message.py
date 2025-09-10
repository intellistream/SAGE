import pytest
from sageflow.utils import create_vector_message

def test_vector_embeddings():
    msg = create_vector_message(1, [1.0, 2.0])
    assert msg.embeddings == [1.0, 2.0]
    assert len(msg.embeddings) == 2

@pytest.mark.parametrize("uid, embeddings, expected_len", [
    (1, [1.0, 2.0], 2),
    (2, [3.0, 4.0, 5.0], 3),
    (3, [], 0),
])
def test_create_vector_message(uid, embeddings, expected_len):
    msg = create_vector_message(uid, embeddings)
    assert msg.embeddings == embeddings
    assert len(msg.embeddings) == expected_len
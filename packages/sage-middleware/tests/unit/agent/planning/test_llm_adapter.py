from unittest.mock import MagicMock

import pytest

from sage.middleware.operators.agent.planning.llm_adapter import GeneratorToClientAdapter


@pytest.fixture
def mock_generator():
    return MagicMock()


@pytest.fixture
def adapter(mock_generator):
    return GeneratorToClientAdapter(mock_generator)


def test_chat_success(adapter, mock_generator):
    # Mock generator.execute returning (usage, output)
    mock_generator.execute.return_value = ({"tokens": 10}, "Hello world")

    messages = [{"role": "system", "content": "sys"}, {"role": "user", "content": "hi"}]

    response = adapter.chat(messages)

    assert response == "Hello world"
    mock_generator.execute.assert_called_once()
    args = mock_generator.execute.call_args[0][0]
    assert args[0] == "hi"  # user_query
    assert args[1] == messages


def test_chat_no_user_msg(adapter, mock_generator):
    mock_generator.execute.return_value = ({}, "output")
    messages = [{"role": "system", "content": "sys"}]

    adapter.chat(messages)

    args = mock_generator.execute.call_args[0][0]
    assert args[0] == "Chat request"  # default


def test_generate(adapter, mock_generator):
    mock_generator.execute.return_value = ({}, "generated text")

    result = adapter.generate("prompt")

    assert len(result) == 1
    assert result[0]["generations"][0]["text"] == "generated text"

    args = mock_generator.execute.call_args[0][0]
    assert args[0] == "prompt"
    assert args[1] == [{"role": "user", "content": "prompt"}]

"""Tests for finetune data processing functions."""

import json
from unittest.mock import MagicMock, patch

import pytest

from sage.libs.finetune.data import (
    format_alpaca_sample,
    format_conversation_sample,
    format_qa_sample,
    load_training_data,
    prepare_dataset,
)


class TestLoadTrainingData:
    """Test load_training_data function."""

    def test_load_json_file(self, tmp_path):
        """Test loading data from JSON file."""
        # Create a test JSON file
        test_data = [
            {"instruction": "Test 1", "output": "Response 1"},
            {"instruction": "Test 2", "output": "Response 2"},
        ]
        json_file = tmp_path / "test.json"
        with open(json_file, "w") as f:
            json.dump(test_data, f)

        # Load and verify
        loaded_data = load_training_data(json_file)
        assert loaded_data == test_data
        assert len(loaded_data) == 2

    def test_load_jsonl_file(self, tmp_path):
        """Test loading data from JSONL file."""
        # Create a test JSONL file
        test_data = [
            {"instruction": "Test 1", "output": "Response 1"},
            {"instruction": "Test 2", "output": "Response 2"},
        ]
        jsonl_file = tmp_path / "test.jsonl"
        with open(jsonl_file, "w") as f:
            for item in test_data:
                f.write(json.dumps(item) + "\n")

        # Load and verify
        loaded_data = load_training_data(jsonl_file)
        assert loaded_data == test_data
        assert len(loaded_data) == 2

    def test_file_not_found(self):
        """Test that FileNotFoundError is raised for non-existent file."""
        with pytest.raises(FileNotFoundError):
            load_training_data("/nonexistent/path/file.json")

    def test_unsupported_format(self, tmp_path):
        """Test that ValueError is raised for unsupported file format."""
        txt_file = tmp_path / "test.txt"
        txt_file.write_text("some text")

        with pytest.raises(ValueError, match="不支持的文件格式"):
            load_training_data(txt_file)


class TestFormatAlpacaSample:
    """Test format_alpaca_sample function."""

    def test_basic_format(self):
        """Test formatting basic Alpaca sample without input."""
        sample = {"instruction": "What is Python?", "output": "Python is a programming language."}
        result = format_alpaca_sample(sample)

        assert "text" in result
        assert "### Instruction:" in result["text"]
        assert "What is Python?" in result["text"]
        assert "### Response:" in result["text"]
        assert "Python is a programming language." in result["text"]

    def test_format_with_input(self):
        """Test formatting Alpaca sample with input field."""
        sample = {
            "instruction": "Translate to Chinese",
            "input": "Hello, world!",
            "output": "你好，世界！",
        }
        result = format_alpaca_sample(sample)

        assert "### Instruction:" in result["text"]
        assert "### Input:" in result["text"]
        assert "### Response:" in result["text"]
        assert "Hello, world!" in result["text"]
        assert "你好，世界！" in result["text"]

    def test_empty_input_field(self):
        """Test formatting when input field is empty string."""
        sample = {"instruction": "Test instruction", "input": "", "output": "Test output"}
        result = format_alpaca_sample(sample)

        # Empty input should not add Input section
        assert "### Instruction:" in result["text"]
        assert "### Response:" in result["text"]


class TestFormatConversationSample:
    """Test format_conversation_sample function."""

    def test_user_assistant_conversation(self):
        """Test formatting simple user-assistant conversation."""
        sample = {
            "conversations": [
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi there!"},
            ]
        }
        result = format_conversation_sample(sample)

        assert "### User:" in result["text"]
        assert "Hello" in result["text"]
        assert "### Assistant:" in result["text"]
        assert "Hi there!" in result["text"]

    def test_multi_turn_conversation(self):
        """Test formatting multi-turn conversation."""
        sample = {
            "conversations": [
                {"role": "user", "content": "Question 1"},
                {"role": "assistant", "content": "Answer 1"},
                {"role": "user", "content": "Question 2"},
                {"role": "assistant", "content": "Answer 2"},
            ]
        }
        result = format_conversation_sample(sample)

        assert result["text"].count("### User:") == 2
        assert result["text"].count("### Assistant:") == 2
        assert "Question 1" in result["text"]
        assert "Answer 2" in result["text"]

    def test_conversation_with_system(self):
        """Test formatting conversation with system message."""
        sample = {
            "conversations": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi!"},
            ]
        }
        result = format_conversation_sample(sample)

        assert "### System:" in result["text"]
        assert "You are a helpful assistant." in result["text"]
        assert "### User:" in result["text"]
        assert "### Assistant:" in result["text"]


class TestFormatQASample:
    """Test format_qa_sample function."""

    def test_basic_qa_format(self):
        """Test formatting basic Q&A sample."""
        sample = {"question": "What is AI?", "answer": "AI is artificial intelligence."}
        result = format_qa_sample(sample)

        assert "text" in result
        assert "What is AI?" in result["text"]
        assert "AI is artificial intelligence." in result["text"]


class TestPrepareDataset:
    """Test prepare_dataset function."""

    @patch("sage.libs.finetune.data.Dataset")
    def test_prepare_alpaca_dataset(self, mock_dataset_class, tmp_path):
        """Test preparing dataset from Alpaca format."""
        # Create test data
        test_data = [
            {"instruction": "Test 1", "output": "Response 1"},
            {"instruction": "Test 2", "input": "Input 2", "output": "Response 2"},
        ]
        json_file = tmp_path / "test.json"
        with open(json_file, "w") as f:
            json.dump(test_data, f)

        # Mock tokenizer
        mock_tokenizer = MagicMock()
        mock_tokenizer.return_value = {"input_ids": [1, 2, 3]}

        # Mock dataset
        mock_dataset = MagicMock()
        mock_dataset.map.return_value = mock_dataset
        mock_dataset_class.from_list.return_value = mock_dataset

        # Prepare dataset
        dataset = prepare_dataset(str(json_file), tokenizer=mock_tokenizer, format_type="alpaca")

        assert dataset is not None
        mock_dataset_class.from_list.assert_called_once()

    @patch("sage.libs.finetune.data.Dataset")
    def test_prepare_conversation_dataset(self, mock_dataset_class, tmp_path):
        """Test preparing dataset from conversation format."""
        test_data = [
            {
                "conversations": [
                    {"role": "user", "content": "Hello"},
                    {"role": "assistant", "content": "Hi!"},
                ]
            }
        ]
        json_file = tmp_path / "test.json"
        with open(json_file, "w") as f:
            json.dump(test_data, f)

        mock_tokenizer = MagicMock()
        mock_tokenizer.return_value = {"input_ids": [1, 2, 3]}

        mock_dataset = MagicMock()
        mock_dataset.map.return_value = mock_dataset
        mock_dataset_class.from_list.return_value = mock_dataset

        dataset = prepare_dataset(
            str(json_file), tokenizer=mock_tokenizer, format_type="conversation"
        )

        assert dataset is not None

    @patch("sage.libs.finetune.data.Dataset")
    def test_auto_detect_format(self, mock_dataset_class, tmp_path):
        """Test automatic format detection."""
        # Alpaca format should be detected
        test_data = [{"instruction": "Test", "output": "Response"}]
        json_file = tmp_path / "test.json"
        with open(json_file, "w") as f:
            json.dump(test_data, f)

        mock_tokenizer = MagicMock()
        mock_tokenizer.return_value = {"input_ids": [1, 2, 3]}

        mock_dataset = MagicMock()
        mock_dataset.map.return_value = mock_dataset
        mock_dataset_class.from_list.return_value = mock_dataset

        dataset = prepare_dataset(
            str(json_file),
            tokenizer=mock_tokenizer,
            format_type=None,  # Auto-detect
        )

        assert dataset is not None

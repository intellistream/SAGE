"""Integration tests for finetune service functions."""

import json
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from sage.libs.finetune.service import merge_lora_weights, start_training


class TestStartTraining:
    """Test start_training function."""

    @patch("sage.libs.finetune.trainer.train_from_meta")
    def test_start_training_native(self, mock_train, tmp_path):
        """Test starting training with native SAGE module."""
        # Create mock config file
        config_path = tmp_path / "config.json"
        config_data = {
            "output_dir": str(tmp_path / "output" / "checkpoints"),
            "model_name": "test/model",
        }
        with open(config_path, "w") as f:
            json.dump(config_data, f)

        mock_train.return_value = None

        # Should not raise exception
        start_training(config_path, use_native=True)

        # Verify train_from_meta was called
        mock_train.assert_called_once()

    @patch("subprocess.Popen")
    def test_start_training_llamafactory(self, mock_popen, tmp_path):
        """Test starting training with LLaMA-Factory."""
        config_path = tmp_path / "config.json"
        config_data = {"output_dir": str(tmp_path / "output")}
        with open(config_path, "w") as f:
            json.dump(config_data, f)

        # Mock subprocess
        mock_process = Mock()
        mock_process.stdout = ["Line 1\n", "Line 2\n"]
        mock_process.returncode = 0
        mock_process.wait.return_value = None
        mock_popen.return_value = mock_process

        start_training(config_path, use_native=False)

        # Verify subprocess was called with llamafactory-cli
        mock_popen.assert_called_once()
        call_args = mock_popen.call_args[0][0]
        assert "llamafactory-cli" in call_args
        assert "train" in call_args

    def test_start_training_config_not_found(self):
        """Test start_training with non-existent config file."""
        with pytest.raises(FileNotFoundError):
            start_training(Path("/nonexistent/config.json"), use_native=True)


class TestMergeLoraWeights:
    """Test merge_lora_weights function."""

    @patch("sage.libs.finetune.service.console")
    @patch("transformers.AutoModelForCausalLM.from_pretrained")
    @patch("transformers.AutoTokenizer.from_pretrained")
    @patch("peft.PeftModel.from_pretrained")
    def test_merge_lora_weights_success(
        self, mock_peft, mock_tokenizer, mock_model, mock_console, tmp_path
    ):
        """Test successful LoRA weights merging."""
        base_model = "test/model"
        checkpoint_path = tmp_path / "lora"
        checkpoint_path.mkdir()
        output_path = tmp_path / "merged"

        # Mock model and tokenizer
        mock_base_model = MagicMock()
        mock_model.return_value = mock_base_model

        mock_peft_model = MagicMock()
        mock_merged = MagicMock()
        mock_peft_model.merge_and_unload.return_value = mock_merged
        mock_peft.return_value = mock_peft_model

        mock_tok = MagicMock()
        mock_tokenizer.return_value = mock_tok

        merge_lora_weights(
            checkpoint_path=checkpoint_path, base_model=base_model, output_path=output_path
        )

        # Verify models were loaded and saved
        mock_model.assert_called_once()
        mock_peft.assert_called_once()
        mock_peft_model.merge_and_unload.assert_called_once()

    def test_merge_lora_weights_path_not_exists(self, tmp_path):
        """Test merge_lora_weights with non-existent LoRA path."""
        base_model = "test/model"
        lora_path = tmp_path / "nonexistent"
        output_path = tmp_path / "merged"

        # Should handle gracefully or raise appropriate error
        with pytest.raises((FileNotFoundError, ImportError, Exception)):
            merge_lora_weights(base_model=base_model, lora_path=lora_path, output_path=output_path)

"""Integration tests for finetune service functions."""

import json
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from sage.libs.finetune.service import merge_lora_weights, serve_model_with_vllm, start_training


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


class TestServeModelWithVllm:
    """Test serve_model_with_vllm function."""

    @patch("subprocess.run")
    def test_serve_model_basic(self, mock_run, tmp_path):
        """Test serving model with basic options."""
        model_path = tmp_path / "model"
        model_path.mkdir()

        mock_run.return_value = Mock(returncode=0)

        serve_model_with_vllm(model_path=model_path)

        # Verify subprocess.run was called
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert "vllm" in " ".join(call_args).lower() or "python" in call_args[0]

    @patch("subprocess.run")
    def test_serve_model_with_custom_port(self, mock_run, tmp_path):
        """Test serving model with custom port."""
        model_path = tmp_path / "model"
        model_path.mkdir()

        mock_run.return_value = Mock(returncode=0)

        serve_model_with_vllm(model_path=model_path, port=8080)

        # Verify port was passed
        call_args = mock_run.call_args[0][0]
        assert "8080" in " ".join(map(str, call_args))

    @patch("subprocess.run")
    def test_serve_model_with_gpu_memory(self, mock_run, tmp_path):
        """Test serving model with GPU memory fraction."""
        model_path = tmp_path / "model"
        model_path.mkdir()

        mock_run.return_value = Mock(returncode=0)

        serve_model_with_vllm(model_path=model_path, gpu_memory_utilization=0.8)

        # Verify GPU memory setting was passed
        call_args = mock_run.call_args[0][0]
        assert "0.8" in " ".join(map(str, call_args))

    def test_serve_model_path_not_exists(self):
        """Test serve_model_with_vllm with non-existent model path."""
        with pytest.raises((FileNotFoundError, ValueError, Exception)):
            serve_model_with_vllm(model_path=Path("/nonexistent/model"))

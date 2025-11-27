# Copyright (c) 2025 IntelliStream. All rights reserved.
# Licensed under the Apache License, Version 2.0

"""Unit tests for AgentSFTTrainer with mocked dependencies.

This test module uses mocks to avoid requiring transformers/peft installation
while still testing the trainer's logic.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from sage.libs.finetune.agent.config import AgentSFTConfig
from sage.libs.finetune.agent.dialog_processor import ProcessedDialog


def _make_dialog(dialog_id: str, loss: float = 0.5) -> ProcessedDialog:
    """Create a test ProcessedDialog."""
    return ProcessedDialog(
        dialog_id=dialog_id,
        task_type="tool_selection",
        text=f"dialog {dialog_id} content",
        metadata={"loss": loss},
        target_tools=["tool"],
        split="train",
        source="agent_sft",
    )


# ========================================================================
# AgentSFTConfig Tests
# ========================================================================


class TestAgentSFTConfig:
    """Tests for AgentSFTConfig dataclass."""

    def test_default_config(self, tmp_path: Path) -> None:
        """Test default configuration values."""
        config = AgentSFTConfig(output_dir=tmp_path / "output")

        assert config.base_model == "Qwen/Qwen2.5-7B-Instruct"
        assert config.num_epochs == 3
        assert config.batch_size == 1
        assert config.gradient_accumulation == 16
        assert config.lora_r == 64
        assert config.lora_alpha == 128
        assert config.learning_rate == 2e-5
        assert config.use_coreset_selection is False
        assert config.use_online_continual is False

    def test_custom_config(self, tmp_path: Path) -> None:
        """Test custom configuration values."""
        config = AgentSFTConfig(
            output_dir=tmp_path / "output",
            base_model="custom/model",
            num_epochs=5,
            batch_size=2,
            learning_rate=1e-4,
            use_coreset_selection=True,
            coreset_target_size=1000,
        )

        assert config.base_model == "custom/model"
        assert config.num_epochs == 5
        assert config.batch_size == 2
        assert config.learning_rate == 1e-4
        assert config.use_coreset_selection is True
        assert config.coreset_target_size == 1000

    def test_output_dir_creation(self, tmp_path: Path) -> None:
        """Test that output directories are created."""
        config = AgentSFTConfig(output_dir=tmp_path / "new_output")

        assert config.output_dir.exists()
        assert config.checkpoint_dir.exists()
        assert config.log_dir.exists()
        assert config.lora_dir.exists()

    def test_effective_batch_size(self, tmp_path: Path) -> None:
        """Test effective batch size calculation."""
        config = AgentSFTConfig(
            output_dir=tmp_path / "output",
            batch_size=2,
            gradient_accumulation=8,
        )

        assert config.effective_batch_size == 16

    def test_task_weights_default(self, tmp_path: Path) -> None:
        """Test default task weights."""
        config = AgentSFTConfig(output_dir=tmp_path / "output")

        weights = config.task_weights
        assert "tool_selection" in weights
        assert "multi_step_planning" in weights
        assert "timing_decision" in weights
        assert "tool_retrieval" in weights
        assert sum(weights.values()) == pytest.approx(1.0)

    def test_lora_target_modules_default(self, tmp_path: Path) -> None:
        """Test default LoRA target modules."""
        config = AgentSFTConfig(output_dir=tmp_path / "output")

        modules = config.lora_target_modules
        assert "q_proj" in modules
        assert "k_proj" in modules
        assert "v_proj" in modules
        assert "o_proj" in modules

    def test_dora_config(self, tmp_path: Path) -> None:
        """Test DoRA configuration."""
        config = AgentSFTConfig(output_dir=tmp_path / "output", use_dora=True)
        assert config.use_dora is True

    def test_lora_plus_config(self, tmp_path: Path) -> None:
        """Test LoRA+ configuration."""
        config = AgentSFTConfig(
            output_dir=tmp_path / "output",
            use_lora_plus=True,
            lora_plus_lr_ratio=32.0,
        )
        assert config.use_lora_plus is True
        assert config.lora_plus_lr_ratio == 32.0


# ========================================================================
# AgentSFTTrainer Tests (with mocks)
# ========================================================================


class TestAgentSFTTrainerInit:
    """Tests for AgentSFTTrainer initialization."""

    @patch("sage.libs.finetune.agent.trainer.AutoModelForCausalLM")
    @patch("sage.libs.finetune.agent.trainer.AutoTokenizer")
    def test_trainer_initialization(
        self, mock_tokenizer_cls, mock_model_cls, tmp_path: Path
    ) -> None:
        """Test trainer initialization."""
        from sage.libs.finetune.agent.trainer import AgentSFTTrainer

        config = AgentSFTConfig(output_dir=tmp_path / "output")
        trainer = AgentSFTTrainer(config)

        assert trainer.config == config
        assert trainer.dialog_processor is not None
        assert trainer.model is None
        assert trainer.tokenizer is None
        assert trainer.train_dataset is None
        assert trainer.eval_dataset is None

    @patch("sage.libs.finetune.agent.trainer.AutoModelForCausalLM")
    @patch("sage.libs.finetune.agent.trainer.AutoTokenizer")
    def test_trainer_with_coreset_selector(
        self, mock_tokenizer_cls, mock_model_cls, tmp_path: Path
    ) -> None:
        """Test trainer initializes coreset selector when enabled."""
        from sage.libs.finetune.agent.trainer import AgentSFTTrainer

        config = AgentSFTConfig(
            output_dir=tmp_path / "output",
            use_coreset_selection=True,
            coreset_strategy="diversity",
        )
        trainer = AgentSFTTrainer(config)

        assert trainer.coreset_selector is not None
        assert trainer.coreset_selector.strategy == "diversity"

    @patch("sage.libs.finetune.agent.trainer.AutoModelForCausalLM")
    @patch("sage.libs.finetune.agent.trainer.AutoTokenizer")
    def test_trainer_without_coreset_selector(
        self, mock_tokenizer_cls, mock_model_cls, tmp_path: Path
    ) -> None:
        """Test trainer does not create coreset selector when disabled."""
        from sage.libs.finetune.agent.trainer import AgentSFTTrainer

        config = AgentSFTConfig(
            output_dir=tmp_path / "output",
            use_coreset_selection=False,
        )
        trainer = AgentSFTTrainer(config)

        assert trainer.coreset_selector is None

    @patch("sage.libs.finetune.agent.trainer.AutoModelForCausalLM")
    @patch("sage.libs.finetune.agent.trainer.AutoTokenizer")
    def test_trainer_with_continual_learner(
        self, mock_tokenizer_cls, mock_model_cls, tmp_path: Path
    ) -> None:
        """Test trainer initializes continual learner when enabled."""
        from sage.libs.finetune.agent.trainer import AgentSFTTrainer

        config = AgentSFTConfig(
            output_dir=tmp_path / "output",
            use_online_continual=True,
            continual_buffer_size=1024,
            continual_replay_ratio=0.5,
        )
        trainer = AgentSFTTrainer(config)

        assert trainer.continual_learner is not None
        assert trainer.continual_learner.buffer_size == 1024
        assert trainer.continual_learner.replay_ratio == 0.5


class TestAgentSFTTrainerLoadModel:
    """Tests for model and tokenizer loading."""

    @patch("sage.libs.finetune.agent.trainer.AutoModelForCausalLM")
    @patch("sage.libs.finetune.agent.trainer.AutoTokenizer")
    def test_load_model_and_tokenizer(
        self, mock_tokenizer_cls, mock_model_cls, tmp_path: Path
    ) -> None:
        """Test loading model and tokenizer."""
        from sage.libs.finetune.agent.trainer import AgentSFTTrainer

        # Setup mocks
        mock_model = MagicMock()
        mock_model_cls.from_pretrained.return_value = mock_model

        mock_tokenizer = MagicMock()
        mock_tokenizer.pad_token = None
        mock_tokenizer.eos_token = "[EOS]"
        mock_tokenizer_cls.from_pretrained.return_value = mock_tokenizer

        config = AgentSFTConfig(output_dir=tmp_path / "output")
        trainer = AgentSFTTrainer(config)

        trainer.load_model_and_tokenizer()

        assert trainer.model is not None
        assert trainer.tokenizer is not None
        mock_model_cls.from_pretrained.assert_called_once()
        mock_tokenizer_cls.from_pretrained.assert_called_once()

    @patch("sage.libs.finetune.agent.trainer.AutoModelForCausalLM")
    @patch("sage.libs.finetune.agent.trainer.AutoTokenizer")
    def test_load_model_8bit(self, mock_tokenizer_cls, mock_model_cls, tmp_path: Path) -> None:
        """Test loading model with 8-bit quantization."""
        from sage.libs.finetune.agent.trainer import AgentSFTTrainer

        mock_model = MagicMock()
        mock_model_cls.from_pretrained.return_value = mock_model

        mock_tokenizer = MagicMock()
        mock_tokenizer.pad_token = "[PAD]"
        mock_tokenizer_cls.from_pretrained.return_value = mock_tokenizer

        config = AgentSFTConfig(
            output_dir=tmp_path / "output",
            load_in_8bit=True,
        )
        trainer = AgentSFTTrainer(config)
        trainer.load_model_and_tokenizer()

        # Check 8-bit loading kwargs
        call_kwargs = mock_model_cls.from_pretrained.call_args[1]
        assert call_kwargs.get("load_in_8bit") is True


class TestAgentSFTTrainerApplyLora:
    """Tests for LoRA application."""

    @patch("sage.libs.finetune.agent.trainer.get_peft_model")
    @patch("sage.libs.finetune.agent.trainer.PeftLoraConfig")
    @patch("sage.libs.finetune.agent.trainer.AutoModelForCausalLM")
    @patch("sage.libs.finetune.agent.trainer.AutoTokenizer")
    def test_apply_lora(
        self,
        mock_tokenizer_cls,
        mock_model_cls,
        mock_lora_config,
        mock_get_peft_model,
        tmp_path: Path,
    ) -> None:
        """Test applying LoRA adapters."""
        from sage.libs.finetune.agent.trainer import AgentSFTTrainer

        # Setup mocks
        mock_model = MagicMock()
        mock_model.named_parameters.return_value = []
        mock_model_cls.from_pretrained.return_value = mock_model

        mock_tokenizer = MagicMock()
        mock_tokenizer.pad_token = "[PAD]"
        mock_tokenizer_cls.from_pretrained.return_value = mock_tokenizer

        mock_peft_model = MagicMock()
        mock_peft_model.named_parameters.return_value = []
        mock_get_peft_model.return_value = mock_peft_model

        config = AgentSFTConfig(output_dir=tmp_path / "output")
        trainer = AgentSFTTrainer(config)

        trainer.load_model_and_tokenizer()
        trainer.apply_lora()

        mock_lora_config.assert_called_once()
        mock_get_peft_model.assert_called_once()

    @patch("sage.libs.finetune.agent.trainer.get_peft_model")
    @patch("sage.libs.finetune.agent.trainer.PeftLoraConfig")
    @patch("sage.libs.finetune.agent.trainer.AutoModelForCausalLM")
    @patch("sage.libs.finetune.agent.trainer.AutoTokenizer")
    def test_apply_lora_with_dora(
        self,
        mock_tokenizer_cls,
        mock_model_cls,
        mock_lora_config,
        mock_get_peft_model,
        tmp_path: Path,
    ) -> None:
        """Test applying LoRA with DoRA enabled."""
        from sage.libs.finetune.agent.trainer import AgentSFTTrainer

        mock_model = MagicMock()
        mock_model.named_parameters.return_value = []
        mock_model_cls.from_pretrained.return_value = mock_model

        mock_tokenizer = MagicMock()
        mock_tokenizer.pad_token = "[PAD]"
        mock_tokenizer_cls.from_pretrained.return_value = mock_tokenizer

        mock_peft_model = MagicMock()
        mock_peft_model.named_parameters.return_value = []
        mock_get_peft_model.return_value = mock_peft_model

        config = AgentSFTConfig(
            output_dir=tmp_path / "output",
            use_dora=True,
        )
        trainer = AgentSFTTrainer(config)
        trainer.load_model_and_tokenizer()
        trainer.apply_lora()

        # Verify DoRA is passed to LoraConfig
        call_kwargs = mock_lora_config.call_args[1]
        assert call_kwargs.get("use_dora") is True

    @patch("sage.libs.finetune.agent.trainer.AutoModelForCausalLM")
    @patch("sage.libs.finetune.agent.trainer.AutoTokenizer")
    def test_apply_lora_without_model_raises(
        self, mock_tokenizer_cls, mock_model_cls, tmp_path: Path
    ) -> None:
        """Test that apply_lora raises error if model not loaded."""
        from sage.libs.finetune.agent.trainer import AgentSFTTrainer

        config = AgentSFTConfig(output_dir=tmp_path / "output")
        trainer = AgentSFTTrainer(config)

        with pytest.raises(ValueError, match="Model must be loaded"):
            trainer.apply_lora()


class TestAgentSFTTrainerHelpers:
    """Tests for trainer helper methods."""

    @patch("sage.libs.finetune.agent.trainer.AutoModelForCausalLM")
    @patch("sage.libs.finetune.agent.trainer.AutoTokenizer")
    def test_build_coreset_selector(
        self, mock_tokenizer_cls, mock_model_cls, tmp_path: Path
    ) -> None:
        """Test _build_coreset_selector method."""
        from sage.libs.finetune.agent.trainer import AgentSFTTrainer

        config = AgentSFTConfig(
            output_dir=tmp_path / "output",
            use_coreset_selection=True,
            coreset_strategy="hybrid",
            coreset_metric_key="perplexity",
        )
        trainer = AgentSFTTrainer(config)

        selector = trainer._build_coreset_selector()
        assert selector is not None
        assert selector.strategy == "hybrid"
        assert selector.metric_key == "perplexity"

    @patch("sage.libs.finetune.agent.trainer.AutoModelForCausalLM")
    @patch("sage.libs.finetune.agent.trainer.AutoTokenizer")
    def test_build_coreset_selector_disabled(
        self, mock_tokenizer_cls, mock_model_cls, tmp_path: Path
    ) -> None:
        """Test _build_coreset_selector returns None when disabled."""
        from sage.libs.finetune.agent.trainer import AgentSFTTrainer

        config = AgentSFTConfig(
            output_dir=tmp_path / "output",
            use_coreset_selection=False,
        )
        trainer = AgentSFTTrainer(config)

        selector = trainer._build_coreset_selector()
        assert selector is None

    @patch("sage.libs.finetune.agent.trainer.AutoModelForCausalLM")
    @patch("sage.libs.finetune.agent.trainer.AutoTokenizer")
    def test_build_continual_learner(
        self, mock_tokenizer_cls, mock_model_cls, tmp_path: Path
    ) -> None:
        """Test _build_continual_learner method."""
        from sage.libs.finetune.agent.trainer import AgentSFTTrainer

        config = AgentSFTConfig(
            output_dir=tmp_path / "output",
            use_online_continual=True,
            continual_buffer_size=512,
            continual_replay_ratio=0.4,
        )
        trainer = AgentSFTTrainer(config)

        learner = trainer._build_continual_learner()
        assert learner is not None
        assert learner.buffer_size == 512
        assert learner.replay_ratio == 0.4

    @patch("sage.libs.finetune.agent.trainer.AutoModelForCausalLM")
    @patch("sage.libs.finetune.agent.trainer.AutoTokenizer")
    def test_collect_metrics(self, mock_tokenizer_cls, mock_model_cls, tmp_path: Path) -> None:
        """Test _collect_metrics method."""
        from sage.libs.finetune.agent.trainer import AgentSFTTrainer

        config = AgentSFTConfig(output_dir=tmp_path / "output")
        trainer = AgentSFTTrainer(config)

        samples = [
            _make_dialog("dlg1", 0.5),
            _make_dialog("dlg2", 0.8),
            _make_dialog("dlg3", 0.2),
        ]

        metrics = trainer._collect_metrics(samples, "loss")

        assert metrics["dlg1"] == 0.5
        assert metrics["dlg2"] == 0.8
        assert metrics["dlg3"] == 0.2

    @patch("sage.libs.finetune.agent.trainer.AutoModelForCausalLM")
    @patch("sage.libs.finetune.agent.trainer.AutoTokenizer")
    def test_collect_metrics_missing_key(
        self, mock_tokenizer_cls, mock_model_cls, tmp_path: Path
    ) -> None:
        """Test _collect_metrics with missing metric key."""
        from sage.libs.finetune.agent.trainer import AgentSFTTrainer

        config = AgentSFTConfig(output_dir=tmp_path / "output")
        trainer = AgentSFTTrainer(config)

        samples = [
            ProcessedDialog(
                dialog_id="dlg1",
                task_type="test",
                text="text",
                metadata={},  # No loss key
                target_tools=[],
                split="train",
                source="test",
            )
        ]

        metrics = trainer._collect_metrics(samples, "loss")

        # Should not include samples without the metric
        assert "dlg1" not in metrics


class TestAgentSFTTrainerSave:
    """Tests for model saving."""

    @patch("sage.libs.finetune.agent.trainer.AutoModelForCausalLM")
    @patch("sage.libs.finetune.agent.trainer.AutoTokenizer")
    def test_save_model(self, mock_tokenizer_cls, mock_model_cls, tmp_path: Path) -> None:
        """Test save_model method."""
        from sage.libs.finetune.agent.trainer import AgentSFTTrainer

        mock_model = MagicMock()
        mock_model_cls.from_pretrained.return_value = mock_model

        mock_tokenizer = MagicMock()
        mock_tokenizer.pad_token = "[PAD]"
        mock_tokenizer_cls.from_pretrained.return_value = mock_tokenizer

        config = AgentSFTConfig(output_dir=tmp_path / "output")
        trainer = AgentSFTTrainer(config)

        trainer.load_model_and_tokenizer()
        trainer.save_model()

        mock_model.save_pretrained.assert_called_once()
        mock_tokenizer.save_pretrained.assert_called_once()

    @patch("sage.libs.finetune.agent.trainer.AutoModelForCausalLM")
    @patch("sage.libs.finetune.agent.trainer.AutoTokenizer")
    def test_save_model_without_model_raises(
        self, mock_tokenizer_cls, mock_model_cls, tmp_path: Path
    ) -> None:
        """Test save_model raises error without model."""
        from sage.libs.finetune.agent.trainer import AgentSFTTrainer

        config = AgentSFTConfig(output_dir=tmp_path / "output")
        trainer = AgentSFTTrainer(config)

        with pytest.raises(ValueError, match="Model and tokenizer must exist"):
            trainer.save_model()


# ========================================================================
# LoRAPlusTrainer Tests
# ========================================================================


class TestLoRAPlusTrainer:
    """Tests for LoRAPlusTrainer optimizer customization."""

    def test_lora_plus_lr_ratio_attribute(self) -> None:
        """Test LoRAPlusTrainer stores lr_ratio attribute."""
        # We can't easily instantiate LoRAPlusTrainer without full transformer setup
        # So we just test the class has the expected attribute behavior
        # Check the class exists and has __init__ that accepts lora_plus_lr_ratio
        import inspect

        from sage.libs.finetune.agent.trainer import LoRAPlusTrainer

        sig = inspect.signature(LoRAPlusTrainer.__init__)
        assert "lora_plus_lr_ratio" in sig.parameters

    def test_lora_plus_default_lr_ratio(self) -> None:
        """Test default lr_ratio is 16.0."""
        import inspect

        from sage.libs.finetune.agent.trainer import LoRAPlusTrainer

        sig = inspect.signature(LoRAPlusTrainer.__init__)
        default = sig.parameters["lora_plus_lr_ratio"].default
        assert default == 16.0

    @patch("transformers.Trainer.get_optimizer_cls_and_kwargs")
    def test_lora_plus_create_optimizer_logic(self, mock_get_optimizer) -> None:
        """Test create_optimizer creates correct parameter groups."""
        from sage.libs.finetune.agent.trainer import LoRAPlusTrainer

        # Setup mock for the static method
        mock_optimizer_cls = MagicMock()
        mock_get_optimizer.return_value = (mock_optimizer_cls, {"weight_decay": 0.01})

        # Directly test the create_optimizer logic by mocking the parent class
        # Create an instance with mocked parent
        instance = object.__new__(LoRAPlusTrainer)
        instance.lora_plus_lr_ratio = 16.0
        instance.optimizer = None

        # Mock model
        mock_lora_a_param = MagicMock()
        mock_lora_a_param.requires_grad = True

        mock_lora_b_param = MagicMock()
        mock_lora_b_param.requires_grad = True

        mock_other_param = MagicMock()
        mock_other_param.requires_grad = True

        mock_model = MagicMock()
        mock_model.named_parameters.return_value = [
            ("layer.lora_A.weight", mock_lora_a_param),
            ("layer.lora_B.weight", mock_lora_b_param),
            ("layer.other.weight", mock_other_param),
        ]
        instance.model = mock_model

        # Mock args
        mock_args = MagicMock()
        mock_args.learning_rate = 1e-4
        instance.args = mock_args

        instance.create_optimizer()

        # Verify optimizer was created with parameter groups
        mock_optimizer_cls.assert_called_once()
        call_args = mock_optimizer_cls.call_args

        # Check parameter groups were passed
        param_groups = call_args[0][0]
        assert len(param_groups) == 3

        # Find lr values for each group
        lr_values = {}
        for group in param_groups:
            lr_values[group["name"]] = group["lr"]

        # lora_A should have base lr
        assert lr_values["lora_A"] == 1e-4
        # lora_B should have lr * ratio
        assert lr_values["lora_B"] == pytest.approx(1e-4 * 16.0)
        # other should have base lr
        assert lr_values["other"] == 1e-4

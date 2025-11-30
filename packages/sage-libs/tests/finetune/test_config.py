"""Tests for finetune configuration classes."""

from pathlib import Path

from sage.libs.finetune.config import LoRAConfig, PresetConfigs, TrainingConfig


class TestLoRAConfig:
    """Test LoRAConfig dataclass."""

    def test_default_values(self):
        """Test that LoRAConfig has correct default values."""
        config = LoRAConfig()
        assert config.r == 8
        assert config.lora_alpha == 16
        assert config.lora_dropout == 0.05
        assert config.bias == "none"
        assert config.task_type == "CAUSAL_LM"

    def test_target_modules_default(self):
        """Test that target_modules has correct default values."""
        config = LoRAConfig()
        assert isinstance(config.target_modules, list)
        assert len(config.target_modules) > 0
        expected_modules = ["q_proj", "v_proj", "k_proj", "o_proj"]
        for module in expected_modules:
            assert module in config.target_modules

    def test_custom_values(self):
        """Test creating LoRAConfig with custom values."""
        config = LoRAConfig(
            r=16,
            lora_alpha=32,
            target_modules=["q_proj", "v_proj"],
            lora_dropout=0.1,
            bias="all",
            task_type="SEQ_2_SEQ_LM",
        )
        assert config.r == 16
        assert config.lora_alpha == 32
        assert config.target_modules == ["q_proj", "v_proj"]
        assert config.lora_dropout == 0.1
        assert config.bias == "all"
        assert config.task_type == "SEQ_2_SEQ_LM"


class TestTrainingConfig:
    """Test TrainingConfig dataclass."""

    def test_default_values(self):
        """Test that TrainingConfig has correct default values."""
        config = TrainingConfig()
        assert config.model_name == "Qwen/Qwen2.5-Coder-1.5B-Instruct"
        assert config.load_in_8bit is True
        assert config.load_in_4bit is False
        assert config.max_length == 1024
        assert config.num_train_epochs == 3
        assert config.per_device_train_batch_size == 1
        assert config.gradient_accumulation_steps == 16
        assert config.learning_rate == 5e-5

    def test_output_dir_default(self):
        """Test that output_dir has correct default path."""
        config = TrainingConfig()
        assert isinstance(config.output_dir, Path)
        assert config.output_dir.parts[-2:] == (".sage", "finetune_output")

    def test_optimization_defaults(self):
        """Test optimization-related defaults."""
        config = TrainingConfig()
        assert config.fp16 is True
        assert config.bf16 is False
        assert config.gradient_checkpointing is True
        assert config.optim == "paged_adamw_8bit"

    def test_logging_defaults(self):
        """Test logging and saving defaults."""
        config = TrainingConfig()
        assert config.logging_steps == 10
        assert config.save_steps == 500
        assert config.save_total_limit == 2

    def test_custom_values(self):
        """Test creating TrainingConfig with custom values."""
        custom_path = Path("/tmp/test_output")
        config = TrainingConfig(
            model_name="test/model",
            load_in_8bit=False,
            load_in_4bit=True,
            max_length=2048,
            output_dir=custom_path,
            num_train_epochs=5,
        )
        assert config.model_name == "test/model"
        assert config.load_in_8bit is False
        assert config.load_in_4bit is True
        assert config.max_length == 2048
        assert config.output_dir == custom_path
        assert config.num_train_epochs == 5


class TestPresetConfigs:
    """Test PresetConfigs class."""

    def test_rtx_3060_preset_exists(self):
        """Test that RTX 3060 preset exists and has correct values."""
        preset = PresetConfigs.rtx_3060()
        assert isinstance(preset, TrainingConfig)
        # Should have memory-efficient settings for RTX 3060
        assert preset.load_in_8bit is True
        assert preset.max_length <= 1024
        assert preset.per_device_train_batch_size == 1
        assert preset.gradient_checkpointing is True

    def test_rtx_4090_preset_exists(self):
        """Test that RTX 4090 preset exists and has correct values."""
        preset = PresetConfigs.rtx_4090()
        assert isinstance(preset, TrainingConfig)
        # Should have better settings for RTX 4090
        assert preset.max_length >= 1024

    def test_a100_preset_exists(self):
        """Test that A100 preset exists and has correct values."""
        preset = PresetConfigs.a100()
        assert isinstance(preset, TrainingConfig)
        # Should have best settings for A100
        assert preset.max_length >= 2048

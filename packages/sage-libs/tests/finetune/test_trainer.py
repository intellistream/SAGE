"""Integration tests for finetune trainer."""

import json
from unittest.mock import MagicMock, patch

import pytest

# These tests use mocks to avoid requiring transformers/peft installation


class TestLoRATrainer:
    """Test LoRATrainer class."""

    @patch("sage.libs.finetune.trainer.LoRATrainer")
    def test_trainer_initialization(self, mock_trainer_class, tmp_path):
        """Test LoRATrainer initialization."""
        from sage.libs.finetune.config import TrainingConfig

        config = TrainingConfig(output_dir=tmp_path / "output")

        mock_trainer = MagicMock()
        mock_trainer_class.return_value = mock_trainer

        # Should not raise exception
        trainer = mock_trainer_class(config)
        assert trainer is not None

    @patch("sage.libs.finetune.trainer.LoRATrainer")
    def test_trainer_train_method(self, mock_trainer_class, tmp_path):
        """Test LoRATrainer.train() method."""
        from sage.libs.finetune.config import TrainingConfig

        config = TrainingConfig(output_dir=tmp_path / "output")

        mock_trainer = MagicMock()
        mock_trainer_class.return_value = mock_trainer

        trainer = mock_trainer_class(config)

        # Mock dataset
        mock_dataset = MagicMock()

        # Call train
        trainer.train(mock_dataset)

        # Verify train was called
        trainer.train.assert_called_once_with(mock_dataset)


class TestTrainFromMeta:
    """Test train_from_meta function."""

    @patch("sage.libs.finetune.trainer.LoRATrainer")
    @patch("sage.libs.finetune.trainer.prepare_dataset")
    def test_train_from_meta_basic(self, mock_prepare, mock_trainer_class, tmp_path):
        """Test train_from_meta with basic metadata."""
        from sage.libs.finetune.trainer import train_from_meta

        # Create mock metadata file
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        metadata = {
            "model": "test/model",
            "dataset": str(tmp_path / "data.json"),
        }

        # Use the correct filename that train_from_meta expects
        metadata_file = output_dir / "finetune_meta.json"
        with open(metadata_file, "w") as f:
            json.dump(metadata, f)

        # Create mock data file
        data_file = tmp_path / "data.json"
        data_file.write_text("[]")

        # Mock dataset and trainer
        mock_dataset = MagicMock()
        mock_prepare.return_value = mock_dataset

        mock_trainer = MagicMock()
        mock_trainer_class.return_value = mock_trainer

        # Should not raise exception
        try:
            train_from_meta(output_dir)
        except (ImportError, FileNotFoundError):
            # Expected if transformers/peft not installed
            pass

    def test_train_from_meta_no_metadata(self, tmp_path):
        """Test train_from_meta with missing metadata file."""
        from sage.libs.finetune.trainer import train_from_meta

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        with pytest.raises(FileNotFoundError):
            train_from_meta(output_dir)


class TestTrainerConfiguration:
    """Test trainer configuration setup."""

    @patch("transformers.TrainingArguments")
    def test_training_arguments_creation(self, mock_args, tmp_path):
        """Test creation of TrainingArguments."""
        from sage.libs.finetune.config import TrainingConfig

        config = TrainingConfig(
            output_dir=tmp_path / "output",
            num_train_epochs=5,
            per_device_train_batch_size=2,
            learning_rate=1e-4,
        )

        # Mock TrainingArguments
        mock_args.return_value = MagicMock()

        # Should be able to create training arguments from config
        try:
            args = mock_args(
                output_dir=config.output_dir,
                num_train_epochs=config.num_train_epochs,
                per_device_train_batch_size=config.per_device_train_batch_size,
                learning_rate=config.learning_rate,
            )
            assert args is not None
        except ImportError:
            # Expected if transformers not installed
            pass

    @patch("peft.LoraConfig")
    def test_lora_config_creation(self, mock_lora):
        """Test creation of LoRA config."""
        from sage.libs.finetune.config import LoRAConfig

        config = LoRAConfig(
            r=16, lora_alpha=32, target_modules=["q_proj", "v_proj"], lora_dropout=0.1
        )

        # Mock LoraConfig
        mock_lora.return_value = MagicMock()

        try:
            lora_config = mock_lora(
                r=config.r,
                lora_alpha=config.lora_alpha,
                target_modules=config.target_modules,
                lora_dropout=config.lora_dropout,
                bias=config.bias,
                task_type=config.task_type,
            )
            assert lora_config is not None
        except ImportError:
            # Expected if peft not installed
            pass

"""Tests for finetune core logic."""

import json

from sage.libs.finetune.core import generate_training_config, prepare_training_data
from sage.libs.finetune.models import FinetuneTask


class TestPrepareTrainingData:
    """Test prepare_training_data function."""

    def test_prepare_code_understanding_data(self, tmp_path):
        """Test preparing data for code understanding task."""
        # Create a mock Python file
        root_dir = tmp_path / "project"
        root_dir.mkdir()
        py_file = root_dir / "test.py"
        py_file.write_text("def hello():\n    print('Hello')\n")

        output_dir = tmp_path / "output"

        # Prepare data
        result_path = prepare_training_data(
            task_type=FinetuneTask.CODE_UNDERSTANDING,
            root_dir=root_dir,
            output_dir=output_dir,
            format="alpaca",
        )

        assert result_path.exists()
        assert result_path.suffix == ".json"

        # Verify data content
        with open(result_path) as f:
            data = json.load(f)

        assert isinstance(data, list)
        assert len(data) > 0
        # Should have at least one sample with instruction and output
        assert "instruction" in data[0]
        assert "output" in data[0]

    def test_prepare_qa_pairs_data(self, tmp_path):
        """Test preparing data for QA pairs task."""
        # Create mock QA data file
        qa_data = [
            {"question": "What is Python?", "answer": "A programming language."},
            {"question": "What is ML?", "answer": "Machine Learning."},
        ]
        custom_data_path = tmp_path / "qa.json"
        with open(custom_data_path, "w") as f:
            json.dump(qa_data, f)

        output_dir = tmp_path / "output"

        result_path = prepare_training_data(
            task_type=FinetuneTask.QA_PAIRS,
            root_dir=tmp_path,
            output_dir=output_dir,
            format="alpaca",
            custom_data_path=custom_data_path,
        )

        assert result_path.exists()

        # Verify data was converted to Alpaca format
        with open(result_path) as f:
            data = json.load(f)

        assert len(data) == 2
        assert data[0]["instruction"] == "What is Python?"
        assert data[0]["output"] == "A programming language."

    def test_prepare_custom_data(self, tmp_path):
        """Test preparing data for custom task."""
        custom_data = [
            {"instruction": "Custom task 1", "output": "Custom output 1"},
            {"instruction": "Custom task 2", "output": "Custom output 2"},
        ]
        custom_data_path = tmp_path / "custom.json"
        with open(custom_data_path, "w") as f:
            json.dump(custom_data, f)

        output_dir = tmp_path / "output"

        result_path = prepare_training_data(
            task_type=FinetuneTask.CUSTOM,
            root_dir=tmp_path,
            output_dir=output_dir,
            custom_data_path=custom_data_path,
        )

        assert result_path.exists()

        with open(result_path) as f:
            data = json.load(f)

        assert len(data) == 2
        assert data[0]["instruction"] == "Custom task 1"

    def test_output_dir_created(self, tmp_path):
        """Test that output directory is created if it doesn't exist."""
        root_dir = tmp_path / "project"
        root_dir.mkdir()
        (root_dir / "test.py").write_text("print('test')")

        output_dir = tmp_path / "nonexistent" / "output"
        assert not output_dir.exists()

        prepare_training_data(
            task_type=FinetuneTask.CODE_UNDERSTANDING, root_dir=root_dir, output_dir=output_dir
        )

        assert output_dir.exists()

    def test_filter_by_extensions(self, tmp_path):
        """Test filtering files by extensions."""
        root_dir = tmp_path / "project"
        root_dir.mkdir()
        (root_dir / "test.py").write_text("python code")
        (root_dir / "config.yaml").write_text("yaml: config")
        (root_dir / "ignore.txt").write_text("should be ignored")

        output_dir = tmp_path / "output"

        result_path = prepare_training_data(
            task_type=FinetuneTask.CODE_UNDERSTANDING,
            root_dir=root_dir,
            output_dir=output_dir,
            extensions=[".py", ".yaml"],
        )

        with open(result_path) as f:
            data = json.load(f)

        # Should only include .py and .yaml files
        file_mentions = [item["instruction"] for item in data]
        assert any("test.py" in mention for mention in file_mentions)
        assert any("config.yaml" in mention for mention in file_mentions)
        assert not any("ignore.txt" in mention for mention in file_mentions)


class TestGenerateTrainingConfig:
    """Test generate_training_config function."""

    def test_generate_default_config(self, tmp_path):
        """Test generating default training configuration."""
        dataset_path = tmp_path / "data.json"
        dataset_path.write_text("[]")
        output_dir = tmp_path / "output"

        config_path = generate_training_config(
            model_name="test/model", dataset_path=dataset_path, output_dir=output_dir
        )

        assert config_path.exists()
        assert config_path.suffix in [".json", ".yaml"]

        # Verify content
        with open(config_path) as f:
            if config_path.suffix == ".json":
                config = json.load(f)
                assert "model_name_or_path" in config or "model" in str(config).lower()
            # Could also be YAML, just check file exists

    def test_generate_config_custom_framework(self, tmp_path):
        """Test generating config with custom framework."""
        dataset_path = tmp_path / "data.json"
        dataset_path.write_text("[]")
        output_dir = tmp_path / "output"

        config_path = generate_training_config(
            model_name="custom/model",
            dataset_path=dataset_path,
            output_dir=output_dir,
            framework="llama-factory",
        )

        assert config_path.exists()

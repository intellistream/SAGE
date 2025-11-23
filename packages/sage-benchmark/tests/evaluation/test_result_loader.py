"""
Tests for ResultLoader
"""

import json
import tempfile
from pathlib import Path

import pytest
from sage.benchmark.benchmark_memory.evaluation.core.result_loader import ResultLoader


class TestResultLoader:
    """Test cases for ResultLoader"""

    def setup_method(self):
        """Setup test fixture with temporary directory"""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)

    def teardown_method(self):
        """Cleanup temporary directory"""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _create_test_result_file(self, filename: str, content: dict) -> Path:
        """Helper to create a test result JSON file"""
        file_path = self.temp_path / filename
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(content, f)
        return file_path

    def test_initialization_valid_path(self):
        """Test initialization with valid path"""
        loader = ResultLoader(self.temp_dir)
        assert loader.folder_path == self.temp_path
        assert isinstance(loader.results, list)

    def test_initialization_invalid_path(self):
        """Test initialization with invalid path"""
        with pytest.raises(FileNotFoundError):
            ResultLoader("/nonexistent/path")

    def test_load_single_result_file(self):
        """Test loading a single result file"""
        result_data = {
            "experiment_info": {"task_id": "test-001"},
            "test_results": [{"test_index": 1, "questions": []}],
        }
        self._create_test_result_file("result1.json", result_data)

        loader = ResultLoader(self.temp_dir)
        assert len(loader.results) == 1
        assert loader.results[0]["experiment_info"]["task_id"] == "test-001"

    def test_load_multiple_result_files(self):
        """Test loading multiple result files"""
        for i in range(3):
            result_data = {
                "experiment_info": {"task_id": f"test-{i:03d}"},
                "test_results": [],
            }
            self._create_test_result_file(f"result{i}.json", result_data)

        loader = ResultLoader(self.temp_dir)
        assert len(loader.results) == 3

    def test_load_empty_directory(self):
        """Test loading from empty directory"""
        loader = ResultLoader(self.temp_dir)
        assert len(loader.results) == 0

    def test_load_invalid_json(self, capsys):
        """Test loading invalid JSON file"""
        invalid_file = self.temp_path / "invalid.json"
        with open(invalid_file, "w") as f:
            f.write("{ invalid json }")

        ResultLoader(self.temp_dir)
        captured = capsys.readouterr()
        assert "JSON 解析失败" in captured.out or "加载失败" in captured.out

    def test_get_all_results(self):
        """Test get_all_results method"""
        result_data = {
            "experiment_info": {"task_id": "test-001"},
            "test_results": [],
        }
        self._create_test_result_file("result.json", result_data)

        loader = ResultLoader(self.temp_dir)
        results = loader.get_all_results()
        assert isinstance(results, list)
        assert len(results) == 1

    def test_get_result_by_task_id_found(self):
        """Test get_result_by_task_id when task exists"""
        for i in range(3):
            result_data = {
                "experiment_info": {"task_id": f"test-{i:03d}"},
                "test_results": [],
            }
            self._create_test_result_file(f"result{i}.json", result_data)

        loader = ResultLoader(self.temp_dir)
        result = loader.get_result_by_task_id("test-001")
        assert result is not None
        assert result["experiment_info"]["task_id"] == "test-001"

    def test_get_result_by_task_id_not_found(self):
        """Test get_result_by_task_id when task doesn't exist"""
        result_data = {
            "experiment_info": {"task_id": "test-001"},
            "test_results": [],
        }
        self._create_test_result_file("result.json", result_data)

        loader = ResultLoader(self.temp_dir)
        result = loader.get_result_by_task_id("nonexistent")
        assert result is None

    def test_get_summary(self):
        """Test get_summary method"""
        for i in range(2):
            result_data = {
                "experiment_info": {"task_id": f"test-{i:03d}"},
                "test_results": [],
            }
            self._create_test_result_file(f"result{i}.json", result_data)

        loader = ResultLoader(self.temp_dir)
        summary = loader.get_summary()
        assert summary["total_files"] == 2
        assert "test-000" in summary["task_ids"]
        assert "test-001" in summary["task_ids"]
        assert summary["folder_path"] == str(self.temp_path)

    def test_validate_result_format_valid(self):
        """Test validate_result_format with valid result"""
        result_data = {
            "experiment_info": {"task_id": "test-001"},
            "test_results": [{"test_index": 1}],
        }
        self._create_test_result_file("result.json", result_data)

        loader = ResultLoader(self.temp_dir)
        is_valid = loader.validate_result_format(loader.results[0])
        assert is_valid is True

    def test_validate_result_format_missing_key(self, capsys):
        """Test validate_result_format with missing required key"""
        result = {"experiment_info": {"task_id": "test"}}  # Missing test_results

        loader = ResultLoader(self.temp_dir)
        is_valid = loader.validate_result_format(result)
        assert is_valid is False
        captured = capsys.readouterr()
        assert "缺少必需字段" in captured.out

    def test_validate_result_format_invalid_test_results(self, capsys):
        """Test validate_result_format with invalid test_results type"""
        result = {
            "experiment_info": {"task_id": "test"},
            "test_results": "not a list",  # Should be list
        }

        loader = ResultLoader(self.temp_dir)
        is_valid = loader.validate_result_format(result)
        assert is_valid is False
        captured = capsys.readouterr()
        assert "应为列表" in captured.out

    def test_file_metadata_added(self):
        """Test that file metadata is added to results"""
        result_data = {
            "experiment_info": {"task_id": "test-001"},
            "test_results": [],
        }
        self._create_test_result_file("my_result.json", result_data)

        loader = ResultLoader(self.temp_dir)
        result = loader.results[0]
        assert "_file_path" in result
        assert "_file_name" in result
        assert result["_file_name"] == "my_result.json"

    def test_recursive_loading(self):
        """Test loading JSON files from subdirectories"""
        # Create subdirectory
        subdir = self.temp_path / "subdir"
        subdir.mkdir()

        # Create file in subdirectory
        result_data = {
            "experiment_info": {"task_id": "test-sub"},
            "test_results": [],
        }
        subdir_file = subdir / "result_sub.json"
        with open(subdir_file, "w", encoding="utf-8") as f:
            json.dump(result_data, f)

        loader = ResultLoader(self.temp_dir)
        assert len(loader.results) == 1
        assert loader.results[0]["experiment_info"]["task_id"] == "test-sub"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

"""Tests for finetune models and enums."""

from sage.libs.finetune.models import TASK_NAMES, FinetuneTask


class TestFinetuneTask:
    """Test FinetuneTask enum."""

    def test_enum_values(self):
        """Test that all enum values are defined correctly."""
        assert FinetuneTask.CODE_UNDERSTANDING == "code"
        assert FinetuneTask.QA_PAIRS == "qa"
        assert FinetuneTask.INSTRUCTION == "instruction"
        assert FinetuneTask.CHAT == "chat"
        assert FinetuneTask.CUSTOM == "custom"

    def test_enum_is_string(self):
        """Test that enum values are strings."""
        for task in FinetuneTask:
            assert isinstance(task.value, str)

    def test_task_names_mapping(self):
        """Test that TASK_NAMES contains all enum values."""
        for task in FinetuneTask:
            assert task in TASK_NAMES
            assert isinstance(TASK_NAMES[task], str)
            assert len(TASK_NAMES[task]) > 0

    def test_task_names_completeness(self):
        """Test that TASK_NAMES has exactly the same keys as FinetuneTask."""
        assert set(TASK_NAMES.keys()) == set(FinetuneTask)

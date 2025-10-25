"""pytest configuration for medical diagnosis tests."""

import json
from pathlib import Path

import pytest


@pytest.fixture(scope="session", autouse=True)
def prepare_minimal_test_data():
    """
    Prepare minimal test data for medical diagnosis tests.

    This fixture automatically runs before any tests in this directory.
    It creates a minimal test dataset if the real data is not available.
    """
    # Get the medical diagnosis app directory
    test_dir = Path(__file__).parent
    app_dir = test_dir.parent.parent / "src" / "sage" / "apps" / "medical_diagnosis"
    data_dir = app_dir / "data" / "processed"
    test_index_path = data_dir / "test_index.json"

    # If real data exists, skip creating mock data
    if test_index_path.exists():
        print(f"✓ Using existing test data at {test_index_path}")
        return

    # Create minimal mock test data
    print(f"✓ Creating minimal test data at {test_index_path}")
    data_dir.mkdir(parents=True, exist_ok=True)

    # Create minimal test cases (no actual images needed for structure tests)
    mock_test_cases = [
        {
            "case_id": "mock_001",
            "patient_id": "P001",
            "age": 45,
            "gender": "男",
            "disease": "正常",
            "severity": "无",
            "image_path": "mock_images/case_001.npy",
        },
        {
            "case_id": "mock_002",
            "patient_id": "P002",
            "age": 52,
            "gender": "女",
            "disease": "椎间盘突出",
            "severity": "中度",
            "image_path": "mock_images/case_002.npy",
        },
    ]

    # Save test index
    with open(test_index_path, "w", encoding="utf-8") as f:
        json.dump(mock_test_cases, f, ensure_ascii=False, indent=2)

    # Create mock image directory
    mock_image_dir = data_dir / "mock_images"
    mock_image_dir.mkdir(parents=True, exist_ok=True)

    # Create placeholder image files (empty numpy arrays)
    import numpy as np

    for case in mock_test_cases:
        image_path = data_dir / case["image_path"]
        if not image_path.exists():
            # Create a minimal numpy array as placeholder
            mock_image = np.zeros((64, 64), dtype=np.float32)
            np.save(image_path, mock_image)

    print(f"✓ Created {len(mock_test_cases)} mock test cases")

#!/usr/bin/env python3
"""
Demo: Feature Extraction with Pretrained Models

This script demonstrates the use of CLIP and DINOv2 models for feature extraction
in the medical diagnosis application.

Issue #894: Use pretrained models for feature extraction instead of random features
"""

import numpy as np

from sage.apps.medical_diagnosis.agents.image_analyzer import (
    TORCH_AVAILABLE,
    ImageAnalyzer,
)


def demo_clip_features():
    """Demonstrate CLIP feature extraction"""
    print("\n" + "=" * 80)
    print("🔬 Demo: CLIP Feature Extraction")
    print("=" * 80)

    config = {
        "models": {"vision_model": "Qwen/Qwen2-VL-7B-Instruct"},
        "image_processing": {
            "feature_extraction": {"method": "clip", "dimension": 512}
        },
    }

    if not TORCH_AVAILABLE:
        print("⚠️  PyTorch not available, will use mock features")
    else:
        print("✅ PyTorch available, attempting to load CLIP model...")

    analyzer = ImageAnalyzer(config)

    # Create a mock medical image
    mock_mri_image = np.random.randint(0, 255, (512, 512), dtype=np.uint8)
    print("\n📸 Created mock MRI image (512x512)")

    # Extract features
    print("\n🔍 Extracting features...")
    features = analyzer._extract_features(mock_mri_image)

    if features is not None:
        print("\n✅ Feature extraction successful!")
        print(f"   - Feature dimension: {features.shape[0]}")
        print(f"   - Feature type: {features.dtype}")
        print(f"   - Feature norm: {np.linalg.norm(features):.4f}")
        print(f"   - Feature range: [{features.min():.4f}, {features.max():.4f}]")

        # Show a few feature values
        print("\n📊 First 10 feature values:")
        print(f"   {features[:10]}")
    else:
        print("\n❌ Feature extraction failed")


def demo_dinov2_features():
    """Demonstrate DINOv2 feature extraction"""
    print("\n" + "=" * 80)
    print("🔬 Demo: DINOv2 Feature Extraction")
    print("=" * 80)

    config = {
        "models": {"vision_model": "Qwen/Qwen2-VL-7B-Instruct"},
        "image_processing": {
            "feature_extraction": {"method": "dinov2", "dimension": 768}
        },
    }

    if not TORCH_AVAILABLE:
        print("⚠️  PyTorch not available, will use mock features")
    else:
        print("✅ PyTorch available, attempting to load DINOv2 model...")

    analyzer = ImageAnalyzer(config)

    # Create a mock medical image
    mock_mri_image = np.random.randint(0, 255, (512, 512), dtype=np.uint8)
    print("\n📸 Created mock MRI image (512x512)")

    # Extract features
    print("\n🔍 Extracting features...")
    features = analyzer._extract_features(mock_mri_image)

    if features is not None:
        print("\n✅ Feature extraction successful!")
        print(f"   - Feature dimension: {features.shape[0]}")
        print(f"   - Feature type: {features.dtype}")
        print(f"   - Feature norm: {np.linalg.norm(features):.4f}")
        print(f"   - Feature range: [{features.min():.4f}, {features.max():.4f}]")

        # Show a few feature values
        print("\n📊 First 10 feature values:")
        print(f"   {features[:10]}")
    else:
        print("\n❌ Feature extraction failed")


def demo_full_analysis():
    """Demonstrate full image analysis pipeline"""
    print("\n" + "=" * 80)
    print("🔬 Demo: Full Image Analysis Pipeline")
    print("=" * 80)

    config = {
        "models": {"vision_model": "Qwen/Qwen2-VL-7B-Instruct"},
        "image_processing": {
            "feature_extraction": {"method": "clip", "dimension": 768}
        },
    }

    analyzer = ImageAnalyzer(config)

    # Analyze a non-existent image (will use mock data)
    print("\n🔍 Running full analysis (using mock data)...")
    result = analyzer.analyze("test_patient_mri.dcm")

    print("\n📊 Analysis Results:")
    print(f"   - Image quality: {result['image_quality']:.2f}")
    print(f"   - Vertebrae detected: {len(result['vertebrae'])}")
    print(f"   - Discs detected: {len(result['discs'])}")
    print(f"   - Abnormalities found: {len(result['abnormalities'])}")

    if result["image_embedding"] is not None:
        print("\n🧬 Image Embedding:")
        print(f"   - Dimension: {result['image_embedding'].shape[0]}")
        print(f"   - Norm: {np.linalg.norm(result['image_embedding']):.4f}")

    print("\n📝 Detected Abnormalities:")
    for i, abnormality in enumerate(result["abnormalities"], 1):
        print(f"   {i}. {abnormality['description']}")
        print(
            f"      Location: {abnormality['location']}, Severity: {abnormality['severity']}"
        )


def main():
    """Main demo function"""
    print("\n" + "=" * 80)
    print("🎯 Medical Image Feature Extraction Demo")
    print("=" * 80)
    print("\nThis demo showcases the integration of pretrained models (CLIP, DINOv2)")
    print("for feature extraction in medical image analysis.")
    print("\nIssue #894: https://github.com/intellistream/SAGE/issues/894")

    # Demo 1: CLIP
    demo_clip_features()

    # Demo 2: DINOv2
    demo_dinov2_features()

    # Demo 3: Full analysis
    demo_full_analysis()

    print("\n" + "=" * 80)
    print("✅ Demo Complete!")
    print("=" * 80)
    print("\n💡 Note: When models are not available (e.g., no PyTorch or GPU),")
    print("   the system automatically falls back to mock features for testing.")
    print("\n")


if __name__ == "__main__":
    main()

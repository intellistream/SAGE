#!/usr/bin/env python3
"""
Medical Diagnosis System Example

This script demonstrates how to use the Medical Diagnosis application from sage-apps.
It provides AI-assisted medical imaging analysis using a multi-agent system.

Requirements:
    pip install -e packages/sage-apps[medical]

Usage:
    python examples/apps/run_medical_diagnosis.py
    python examples/apps/run_medical_diagnosis.py --case-id case_0001
    python examples/apps/run_medical_diagnosis.py --interactive
"""

import argparse
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

try:
    from sage.apps.medical_diagnosis.run_diagnosis import main as diagnosis_main
except ImportError as e:
    print(f"Error importing sage.apps.medical_diagnosis: {e}")
    print("\nPlease install sage-apps with medical dependencies:")
    print("  pip install -e packages/sage-apps[medical]")
    sys.exit(1)


def main():
    """Run the medical diagnosis system."""
    parser = argparse.ArgumentParser(
        description="SAGE Medical Diagnosis System - AI-assisted medical imaging analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run with default demo case
  python %(prog)s
  
  # Analyze a specific case
  python %(prog)s --case-id case_0001
  
  # Interactive mode
  python %(prog)s --interactive
  
  # Use custom data directory
  python %(prog)s --data-dir path/to/medical/data

Features:
  - Multi-agent diagnostic workflow
  - Medical image analysis
  - Knowledge base integration
  - Diagnostic report generation
  - Interactive consultation mode
        """
    )
    
    parser.add_argument(
        "--case-id",
        type=str,
        help="Specific case ID to analyze (e.g., case_0001)"
    )
    
    parser.add_argument(
        "--data-dir",
        type=str,
        default="packages/sage-apps/src/sage/apps/medical_diagnosis/data",
        help="Path to medical diagnosis data directory"
    )
    
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Run in interactive consultation mode"
    )
    
    parser.add_argument(
        "--output",
        type=str,
        help="Output directory for diagnostic reports"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    # Validate data directory
    data_path = Path(args.data_dir)
    if not data_path.exists():
        print(f"Error: Data directory not found: {args.data_dir}")
        print("\nExpected structure:")
        print("  {data_dir}/processed/images/")
        print("  {data_dir}/processed/all_cases.json")
        sys.exit(1)
    
    print("=" * 60)
    print("SAGE Medical Diagnosis System")
    print("=" * 60)
    print(f"Data Directory: {args.data_dir}")
    if args.case_id:
        print(f"Case ID: {args.case_id}")
    if args.interactive:
        print("Mode: Interactive")
    else:
        print("Mode: Automated Analysis")
    if args.output:
        print(f"Output: {args.output}")
    print("=" * 60)
    print()
    
    # Call the medical diagnosis main function
    try:
        diagnosis_main()
    except Exception as e:
        print(f"Error running medical diagnosis system: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

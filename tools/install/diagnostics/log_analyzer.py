#!/usr/bin/env python3
import argparse
import json
from collections import Counter


def analyze_logs(log_file):
    """Analyzes the JSON log file and prints a summary."""
    with open(log_file) as f:
        logs = [json.loads(line) for line in f]

    print(f"Log file: {log_file}")
    print(f"Total log entries: {len(logs)}")

    # Log level distribution
    level_counts = Counter(log["level"] for log in logs)
    print("\nLog Level Distribution:")
    for level, count in level_counts.items():
        print(f"  {level}: {count}")

    # Phases
    phases = sorted({log["phase"] for log in logs if log.get("phase")})
    print("\nInstallation Phases:")
    for phase in phases:
        print(f"  - {phase}")

    # Errors
    errors = [log for log in logs if log["level"] == "ERROR"]
    if errors:
        print("\nErrors:")
        for error in errors:
            print(
                f"  - [{error['timestamp']}] [{error['context']}/{error['phase']}] {error['message']}"
            )
    else:
        print("\nNo errors found.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analyze SAGE installation logs.")
    parser.add_argument("log_file", help="Path to the install.log file.")
    args = parser.parse_args()

    analyze_logs(args.log_file)

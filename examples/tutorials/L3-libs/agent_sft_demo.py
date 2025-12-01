"""
Agent SFT + Eval Usage Demo

Demonstrates the complete workflow of using agent_sft data source
and agent_eval usage profiles.
"""

from sage.data.sources.agent_sft import AgentSFTDataLoader


def demo_agent_sft_loader():
    """Demonstrate AgentSFTDataLoader functionality."""
    print("=" * 70)
    print("AGENT SFT DATA SOURCE DEMO")
    print("=" * 70)
    print()

    # Initialize loader
    print("1. Initializing AgentSFTDataLoader...")
    loader = AgentSFTDataLoader()
    print("   ✓ Loader initialized successfully")
    print()

    # Display statistics
    print("2. Dataset Statistics:")
    stats = loader.get_stats()
    print(f"   Total dialogs: {stats.total_dialogs}")
    print(f"   - Train: {stats.train_count}")
    print(f"   - Dev: {stats.dev_count}")
    print(f"   - Test: {stats.test_count}")
    print(f"   Average turns per dialog: {stats.avg_turns}")
    print(f"   Average tools per dialog: {stats.avg_tools_per_dialog}")
    print(f"   Unique tools used: {stats.unique_tools}")
    print()

    # Show top tools
    print("3. Top 5 Most Used Tools:")
    sorted_tools = sorted(stats.tool_coverage.items(), key=lambda x: x[1], reverse=True)
    for i, (tool_id, count) in enumerate(sorted_tools[:5], 1):
        print(f"   {i}. {tool_id}: {count} dialogs")
    print()

    # Demonstrate iteration
    print("4. Sample Dialogs from Training Set:")
    for i, dialog in enumerate(loader.iter_dialogs("train")):
        if i >= 2:  # Show only 2 dialogs
            break
        print(f"\n   Dialog {dialog.dialog_id}:")
        print(f"   Goal: {dialog.goal}")
        print(f"   Tools: {', '.join(dialog.target_tools)}")
        print(f"   Turns: {len(dialog.turns)}")
        print("   First 3 turns:")
        for j, turn in enumerate(dialog.turns[:3], 1):
            content_preview = (
                turn.content[:50] + "..." if len(turn.content) > 50 else turn.content
            )
            print(f"      {j}. [{turn.role}] {content_preview}")
    print()

    # Demonstrate batch sampling
    print("5. Batch Sampling:")
    batch = loader.sample_batch(batch_size=5, split="train", shuffle=False)
    print(f"   Sampled {len(batch)} dialogs for training")
    for dialog in batch:
        print(f"   - {dialog.dialog_id}: {dialog.goal[:40]}...")
    print()

    # Demonstrate filtering
    print("6. Filtering by Difficulty:")
    hard_dialogs = loader.filter_by_difficulty("hard", split="test")
    print(f"   Found {len(hard_dialogs)} hard dialogs in test set")
    if hard_dialogs:
        print(f"   Example: {hard_dialogs[0].dialog_id} - {hard_dialogs[0].goal}")
    print()

    # Demonstrate tool filtering
    print("7. Filtering by Tool:")
    if stats.tool_coverage:
        sample_tool = list(stats.tool_coverage.keys())[0]
        tool_dialogs = loader.filter_by_tool(sample_tool, split="train")
        print(
            f"   Tool '{sample_tool}' is used in {len(tool_dialogs)} training dialogs"
        )
    print()

    # Demonstrate dialog lookup
    print("8. Dialog Lookup by ID:")
    dialog = loader.get_dialog("sft_000001")
    if dialog:
        print(f"   Found dialog: {dialog.dialog_id}")
        print(f"   Goal: {dialog.goal}")
        print(f"   Split: {dialog.split}")
    else:
        print("   Dialog not found (may have been filtered out due to validation)")
    print()

    print("=" * 70)
    print("✓ DEMO COMPLETED SUCCESSFULLY")
    print("=" * 70)


def demo_usage_profiles():
    """Demonstrate agent_eval usage profiles (conceptual)."""
    print("\n" + "=" * 70)
    print("AGENT EVAL USAGE PROFILES (Conceptual Demo)")
    print("=" * 70)
    print()

    print("Profile Configurations:")
    print()

    print("1. quick_eval:")
    print("   - Purpose: Fast validation during development")
    print("   - Sources: agent_benchmark")
    print("   - Tasks: tool_selection only")
    print("   - Split: dev (100 samples max)")
    print("   - Use: CI testing, rapid iteration")
    print()

    print("2. full_eval:")
    print("   - Purpose: Comprehensive model evaluation")
    print("   - Sources: agent_benchmark + agent_tools")
    print("   - Tasks: tool_selection, task_planning, timing_judgment")
    print("   - Split: test")
    print("   - Use: Final benchmarks, paper results")
    print()

    print("3. sft_training:")
    print("   - Purpose: Agent model training")
    print("   - Sources: agent_sft + agent_tools")
    print("   - Split: train")
    print("   - Parameters: batch_size=32, max_turns=12, shuffle=true")
    print("   - Use: Supervised fine-tuning workflows")
    print()

    print("Integration Example:")
    print("""
    from sage.data import DataManager

    # Load usage
    manager = DataManager.get_instance()
    agent_eval = manager.get_by_usage("agent_eval")

    # Quick evaluation
    quick = agent_eval.load_profile("quick_eval")
    for sample in quick["benchmark"].iter_split("tool_selection", "dev"):
        # Run fast evaluation
        ...

    # Full evaluation
    full = agent_eval.load_profile("full_eval")
    benchmark = full["benchmark"]
    tools = full["tools"]
    # Run comprehensive tests
    ...

    # SFT training
    sft = agent_eval.load_profile("sft_training")
    training_data = sft["sft"]
    # Train model
    ...
    """)

    print("=" * 70)


def main():
    """Run all demos."""
    # Demo 1: Agent SFT DataLoader
    demo_agent_sft_loader()

    # Demo 2: Usage Profiles (conceptual, since other sources aren't implemented yet)
    demo_usage_profiles()

    print("\n✅ All demos completed successfully!")
    print("\nNote: Full integration requires:")
    print("  - Subtask 1: agent_tools data source")
    print("  - Subtask 2: agent_benchmark data source")
    print("  - DataManager registration (may be automatic)")


if __name__ == "__main__":
    main()

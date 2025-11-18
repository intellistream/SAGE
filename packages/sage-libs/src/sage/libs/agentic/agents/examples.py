"""
SAGE Agents - Usage Examples

This file demonstrates how to use the SAGE agents framework and pre-built bots.

Layer: L3 (Core - Algorithm Library)
"""


def example_basic_bot_usage():
    """
    Example 1: Using pre-built bots

    Demonstrates how to use the pre-built bot implementations
    for common tasks.
    """
    print("=" * 60)
    print("Example 1: Using Pre-built Bots")
    print("=" * 60)

    try:
        from sage.libs.agentic.agents.bots.answer_bot import AnswerBot
        from sage.libs.agentic.agents.bots.question_bot import QuestionBot

        # Create bot instances
        AnswerBot(config={"name": "AnswerBot"})
        QuestionBot(config={"name": "QuestionBot"})

        print("\n✓ Created AnswerBot")
        print("✓ Created QuestionBot")

        # Example usage (mock - actual usage requires LLM setup)
        print("\nNote: Actual bot execution requires LLM configuration")
        print("See README.md for setup instructions")

    except ImportError as e:
        print(f"✗ Import error: {e}")
        print("Make sure sage-libs is properly installed")


def example_agent_workflow():
    """
    Example 2: Multi-agent workflow

    Demonstrates a simple workflow with multiple agents collaborating.
    """
    print("\n" + "=" * 60)
    print("Example 2: Multi-Agent Workflow")
    print("=" * 60)

    try:
        from sage.libs.agentic.agents.bots.answer_bot import AnswerBot
        from sage.libs.agentic.agents.bots.critic_bot import CriticBot
        from sage.libs.agentic.agents.bots.question_bot import QuestionBot

        # Create a workflow: Question → Answer → Critique
        workflow = {
            "questioner": QuestionBot(config={"role": "Questioner"}),
            "answerer": AnswerBot(config={"role": "Answerer"}),
            "critic": CriticBot(config={"role": "Critic"}),
        }

        print("\n✓ Created multi-agent workflow:")
        for role, agent in workflow.items():
            print(f"  - {role}: {agent.__class__.__name__}")

        print("\nWorkflow pattern:")
        print("  1. Questioner generates clarifying questions")
        print("  2. Answerer provides responses")
        print("  3. Critic evaluates the quality")

    except ImportError as e:
        print(f"✗ Import error: {e}")


def example_custom_bot():
    """
    Example 3: Creating a custom bot

    Demonstrates how to extend the base bot classes to create
    custom agents for specific tasks.
    """
    print("\n" + "=" * 60)
    print("Example 3: Creating Custom Bots")
    print("=" * 60)

    print("\nTo create a custom bot:")
    print("1. Import the base bot class or an existing bot")
    print("2. Subclass it and override necessary methods")
    print("3. Implement your custom logic")

    print("\nExample code:")
    print(
        """
    from sage.libs.agentic.agents.bots.answer_bot import AnswerBot

    class CustomDomainBot(AnswerBot):
        def __init__(self, domain: str, **kwargs):
            super().__init__(**kwargs)
            self.domain = domain

        def generate_answer(self, question: str, context: str = "") -> str:
            # Add domain-specific processing
            enhanced_question = f"[{self.domain}] {question}"
            return super().generate_answer(enhanced_question, context)

    # Usage
    medical_bot = CustomDomainBot(domain="Medical", config={"model": "gpt-4"})
    """
    )


def example_bot_integration():
    """
    Example 4: Integrating bots with SAGE pipeline

    Demonstrates how to integrate agent bots into a SAGE pipeline.
    """
    print("\n" + "=" * 60)
    print("Example 4: Bot Integration with SAGE Pipeline")
    print("=" * 60)

    print("\nIntegration pattern:")
    print("1. Create bot instances")
    print("2. Wrap bots as pipeline operators")
    print("3. Connect to data sources and sinks")

    print("\nExample pipeline:")
    print(
        """
    from sage.libs.foundation.io.source import FileSource
    from sage.libs.foundation.io.sink import TerminalSink
    from sage.libs.agentic.agents.bots.answer_bot import AnswerBot

    # Create components
    source = FileSource("questions.txt")
    bot = AnswerBot(config={"model": "gpt-4"})
    sink = TerminalSink()

    # Build pipeline
    for question in source:
        answer = bot.generate_answer(question)
        sink.write(answer)
    """
    )


def run_all_examples():
    """Run all examples in sequence."""
    print("\n" + "=" * 60)
    print("SAGE Agents - Complete Examples")
    print("=" * 60)

    example_basic_bot_usage()
    example_agent_workflow()
    example_custom_bot()
    example_bot_integration()

    print("\n" + "=" * 60)
    print("✓ All examples completed")
    print("=" * 60)
    print("\nFor more information:")
    print("- See agents/README.md for detailed documentation")
    print("- Check agents/bots/README.md for bot-specific guides")
    print("- Visit docs/ for architecture and design patterns")


if __name__ == "__main__":
    run_all_examples()

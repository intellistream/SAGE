#!/usr/bin/env python3
"""
Prepare Timing Judgment Dataset

Generates synthetic data for timing detection benchmark:
- 500+ samples where tool calling IS needed (real-time info, actions, etc.)
- 500+ samples where tool calling is NOT needed (factual, conversational, etc.)

Output format: JSONL with fields:
- sample_id: Unique identifier
- message: User message text
- should_call_tool: Boolean ground truth
- direct_answer: Optional answer if no tool needed
- context: Optional conversation context
- category: Category for analysis

Default output: .sage/benchmark/data/timing_judgment/

Usage:
    python prepare_timing_data.py
    python prepare_timing_data.py --output /path/to/data --num-tool-needed 1000
"""

import argparse
import json
import random
from pathlib import Path
from typing import Any

# Setup paths
SCRIPT_DIR = Path(__file__).resolve().parent
BENCHMARK_AGENT_DIR = SCRIPT_DIR.parent.parent
BENCHMARK_ROOT = BENCHMARK_AGENT_DIR.parent.parent.parent  # sage-benchmark
SAGE_ROOT = BENCHMARK_ROOT.parent.parent  # SAGE repo root

# Default output in .sage/
DEFAULT_OUTPUT_DIR = SAGE_ROOT / ".sage" / "benchmark" / "data" / "timing_judgment"

# Seed for reproducibility
random.seed(42)


# =============================================================================
# Template Categories for SHOULD CALL TOOL (needs real-time or action)
# =============================================================================

TOOL_NEEDED_TEMPLATES = {
    "weather": {
        "templates": [
            "What's the weather like in {city} right now?",
            "Will it rain in {city} tomorrow?",
            "What's the current temperature in {city}?",
            "Is it going to be sunny in {city} this weekend?",
            "What's the weather forecast for {city} next week?",
            "Should I bring an umbrella in {city} today?",
            "How hot is it in {city} today?",
            "What's the humidity level in {city}?",
            "Is there a storm coming to {city}?",
            "What's the UV index in {city} right now?",
        ],
        "variables": {
            "city": [
                "New York",
                "London",
                "Tokyo",
                "Paris",
                "Sydney",
                "Berlin",
                "Singapore",
                "Dubai",
                "San Francisco",
                "Seattle",
                "Beijing",
                "Mumbai",
            ]
        },
    },
    "stock_market": {
        "templates": [
            "What's the current price of {stock}?",
            "How is {stock} performing today?",
            "Show me the stock chart for {stock}",
            "What's the market cap of {company}?",
            "Has {stock} gone up or down today?",
            "What's the trading volume for {stock}?",
            "Give me the latest news about {company} stock",
            "What's {stock}'s 52-week high?",
            "How much has {stock} changed this week?",
            "What are analysts saying about {stock}?",
        ],
        "variables": {
            "stock": ["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA", "META", "NVDA", "AMD", "NFLX"],
            "company": [
                "Apple",
                "Google",
                "Microsoft",
                "Amazon",
                "Tesla",
                "Meta",
                "NVIDIA",
                "AMD",
                "Netflix",
            ],
        },
    },
    "search_query": {
        "templates": [
            "Search for the latest news about {topic}",
            "Find information about {topic}",
            "Look up recent developments in {topic}",
            "Can you search for {topic} articles?",
            "I need to find details about {topic}",
            "Search the web for {topic}",
            "Find me the best resources about {topic}",
            "What's the latest on {topic}?",
            "Can you look up {topic} for me?",
            "Search for {topic} and summarize the results",
        ],
        "variables": {
            "topic": [
                "AI regulations",
                "climate change solutions",
                "cryptocurrency trends",
                "remote work policies",
                "electric vehicles",
                "renewable energy",
                "space exploration",
                "quantum computing",
                "biotechnology",
                "cybersecurity threats",
            ]
        },
    },
    "calculations": {
        "templates": [
            "Calculate the compound interest on ${amount} at {rate}% for {years} years",
            "What's the monthly payment on a ${amount} mortgage at {rate}%?",
            "Convert {amount} USD to EUR",
            "Calculate {num1} raised to the power of {num2}",
            "What's the square root of {number}?",
            "Calculate the area of a circle with radius {radius}",
            "What's {percentage}% of {number}?",
            "Calculate the tip for a ${amount} bill at {percentage}%",
            "Convert {temp}°F to Celsius",
            "What's the BMI for someone {height}cm tall and {weight}kg?",
        ],
        "variables": {
            "amount": ["10000", "50000", "100000", "250000", "500000"],
            "rate": ["3.5", "4.5", "5.0", "6.0", "7.5"],
            "years": ["5", "10", "15", "20", "30"],
            "num1": ["2", "3", "5", "7", "10"],
            "num2": ["8", "10", "12", "15", "20"],
            "number": ["144", "256", "625", "1024", "2048"],
            "radius": ["5", "10", "15", "20", "25"],
            "percentage": ["15", "18", "20", "25", "30"],
            "temp": ["32", "68", "98.6", "100", "212"],
            "height": ["160", "170", "175", "180", "185"],
            "weight": ["50", "60", "70", "80", "90"],
        },
    },
    "real_time_info": {
        "templates": [
            "What time is it in {city}?",
            "What's the current exchange rate for {currency}?",
            "What events are happening in {city} today?",
            "What's trending on social media right now?",
            "What are the latest sports scores for {team}?",
            "Is the {place} open right now?",
            "What's the traffic like on {road}?",
            "What flights are available from {origin} to {destination} tomorrow?",
            "What's the air quality index in {city}?",
            "When is the next bus/train to {destination}?",
        ],
        "variables": {
            "city": ["New York", "London", "Tokyo", "Paris", "Sydney", "Berlin"],
            "currency": ["EUR/USD", "GBP/USD", "JPY/USD", "BTC/USD", "ETH/USD"],
            "team": [
                "Lakers",
                "Yankees",
                "Manchester United",
                "Real Madrid",
                "Patriots",
                "Warriors",
            ],
            "place": ["Central Park", "Louvre Museum", "Empire State Building", "British Museum"],
            "road": ["I-95", "Highway 101", "M25", "Autobahn A1"],
            "origin": ["NYC", "LAX", "LHR", "NRT", "SFO"],
            "destination": ["Paris", "Tokyo", "London", "Sydney", "Berlin"],
        },
    },
    "data_operations": {
        "templates": [
            "Create a spreadsheet with {columns}",
            "Generate a report on {topic}",
            "Export this data to {format}",
            "Create a chart showing {data}",
            "Analyze this dataset for {analysis}",
            "Schedule a meeting for {time}",
            "Send an email to {recipient} about {subject}",
            "Create a reminder for {task}",
            "Book a {type} appointment for {date}",
            "Update the {document} with new information",
        ],
        "variables": {
            "columns": [
                "sales and expenses",
                "revenue by region",
                "employee performance",
            ],
            "topic": ["quarterly sales", "customer feedback", "market trends"],
            "format": ["CSV", "PDF", "Excel", "JSON"],
            "data": ["monthly revenue", "user growth", "conversion rates"],
            "analysis": ["trends", "anomalies", "correlations", "predictions"],
            "time": ["tomorrow 3pm", "next Monday", "next week"],
            "recipient": ["the team", "my manager", "the client"],
            "subject": ["project update", "meeting notes", "proposal"],
            "task": ["submit report", "call client", "review document"],
            "type": ["doctor", "dentist", "car service", "haircut"],
            "date": ["tomorrow", "next Tuesday", "next week"],
            "document": ["project plan", "budget report", "contract"],
        },
    },
    "code_execution": {
        "templates": [
            "Run this Python code: {code}",
            "Execute this script and show output",
            "Debug this code snippet for me",
            "Test this function with input {input}",
            "Compile and run this program",
            "Check if this code has any syntax errors",
            "Profile this code for performance",
            "Run unit tests for this module",
            "Execute this SQL query: {query}",
            "Run this bash command: {command}",
        ],
        "variables": {
            "code": ["print('hello')", "sum([1,2,3])", "list(range(10))"],
            "input": ["[1,2,3]", "'hello world'", "{'key': 'value'}"],
            "query": ["SELECT * FROM users", "INSERT INTO logs", "UPDATE records"],
            "command": ["ls -la", "grep -r 'pattern'", "find . -name '*.py'"],
        },
    },
    "file_operations": {
        "templates": [
            "Open the file {filename}",
            "Save this document as {filename}",
            "Delete the file {filename}",
            "Rename {old_name} to {new_name}",
            "Create a new folder called {folder}",
            "Move {filename} to {destination}",
            "Copy {filename} to clipboard",
            "Compress these files into a zip",
            "Extract the contents of {archive}",
            "List all files in {directory}",
        ],
        "variables": {
            "filename": ["report.pdf", "data.csv", "notes.txt", "presentation.pptx"],
            "old_name": ["draft.doc", "temp.txt", "old_version.py"],
            "new_name": ["final.doc", "important.txt", "new_version.py"],
            "folder": ["Projects", "Archive", "Backup", "Downloads"],
            "destination": ["Desktop", "Documents", "shared folder"],
            "archive": ["files.zip", "backup.tar.gz", "data.rar"],
            "directory": ["current folder", "home directory", "project folder"],
        },
    },
}


# =============================================================================
# Template Categories for NO TOOL NEEDED (factual, conversational)
# =============================================================================

NO_TOOL_TEMPLATES = {
    "factual_knowledge": {
        "templates": [
            "What is the capital of {country}?",
            "Who wrote {book}?",
            "What year did {event} happen?",
            "What is the chemical formula for {compound}?",
            "Who invented the {invention}?",
            "What is the largest {category} in the world?",
            "What language is spoken in {country}?",
            "How many {unit} are in a {larger_unit}?",
            "What is the speed of {thing}?",
            "What is {term} in {subject}?",
        ],
        "variables": {
            "country": [
                "France",
                "Japan",
                "Brazil",
                "Canada",
                "Egypt",
                "India",
                "Germany",
                "Australia",
            ],
            "book": [
                "1984",
                "Pride and Prejudice",
                "The Great Gatsby",
                "Hamlet",
                "Don Quixote",
            ],
            "event": [
                "World War II ended",
                "the Moon landing",
                "the French Revolution started",
            ],
            "compound": ["water", "salt", "carbon dioxide", "methane", "glucose"],
            "invention": ["telephone", "light bulb", "printing press", "automobile", "airplane"],
            "category": ["ocean", "desert", "mountain", "river", "country by area"],
            "unit": ["inches", "ounces", "minutes", "centimeters", "grams"],
            "larger_unit": ["foot", "pound", "hour", "meter", "kilogram"],
            "thing": ["light", "sound in air", "the Earth's rotation"],
            "term": ["photosynthesis", "mitosis", "gravity", "entropy", "algorithm"],
            "subject": ["biology", "physics", "chemistry", "computer science", "mathematics"],
        },
    },
    "definitions": {
        "templates": [
            "What does {word} mean?",
            "Define {term}",
            "Explain the concept of {concept}",
            "What is the definition of {term}?",
            "What does the term {term} refer to?",
            "Can you explain {concept} to me?",
            "What is meant by {phrase}?",
            "How would you define {term}?",
            "What's the meaning of {word}?",
            "Describe what {concept} is",
        ],
        "variables": {
            "word": [
                "ephemeral",
                "ubiquitous",
                "paradigm",
                "synergy",
                "pragmatic",
                "ambiguous",
            ],
            "term": [
                "machine learning",
                "blockchain",
                "quantum computing",
                "democracy",
                "inflation",
            ],
            "concept": [
                "natural selection",
                "supply and demand",
                "cognitive dissonance",
                "relativity",
            ],
            "phrase": [
                "catch-22",
                "the butterfly effect",
                "Occam's razor",
                "the Dunning-Kruger effect",
            ],
        },
    },
    "explanations": {
        "templates": [
            "How does {process} work?",
            "Why do {phenomenon} happen?",
            "What causes {effect}?",
            "Explain how {technology} functions",
            "What is the process of {process}?",
            "How is {product} made?",
            "Why is {fact} true?",
            "What's the difference between {thing1} and {thing2}?",
            "How did {historical_thing} develop?",
            "What are the principles behind {concept}?",
        ],
        "variables": {
            "process": ["photosynthesis", "digestion", "respiration", "nuclear fission"],
            "phenomenon": ["rainbows", "earthquakes", "auroras", "tides", "seasons"],
            "effect": ["global warming", "inflation", "muscle growth", "sleep deprivation"],
            "technology": ["GPS", "WiFi", "batteries", "solar panels", "vaccines"],
            "product": ["paper", "glass", "steel", "chocolate", "bread"],
            "fact": ["the sky blue", "ice floats", "water wet"],
            "thing1": ["mitosis", "weather", "RAM", "HTTP", "DNA"],
            "thing2": ["meiosis", "climate", "ROM", "HTTPS", "RNA"],
            "historical_thing": ["democracy", "the internet", "writing systems", "agriculture"],
            "concept": ["encryption", "machine learning", "evolution", "capitalism"],
        },
    },
    "conversational": {
        "templates": [
            "Hello, how are you?",
            "Thank you for your help!",
            "That's interesting!",
            "I see, that makes sense",
            "Can you tell me more?",
            "That's a good point",
            "I appreciate your explanation",
            "What do you think about that?",
            "Interesting perspective!",
            "Thanks for clarifying",
            "Got it, thanks!",
            "I understand now",
            "That's helpful to know",
            "Good to know!",
            "Makes sense to me",
            "I agree with you",
            "That's a fair point",
            "Well said!",
            "I hadn't thought of it that way",
            "That's very clear, thank you",
        ],
        "variables": {},
    },
    "opinions": {
        "templates": [
            "What are the pros and cons of {topic}?",
            "What do you think about {topic}?",
            "Is {thing} a good idea?",
            "Should I {action}?",
            "What are your thoughts on {topic}?",
            "Do you think {statement}?",
            "What's your opinion on {topic}?",
            "Is it better to {option1} or {option2}?",
            "What are the advantages of {thing}?",
            "How do you feel about {topic}?",
        ],
        "variables": {
            "topic": [
                "remote work",
                "electric cars",
                "social media",
                "AI in education",
                "cryptocurrency",
            ],
            "thing": [
                "learning multiple languages",
                "investing in stocks",
                "starting a business",
            ],
            "action": [
                "learn programming",
                "switch careers",
                "pursue a PhD",
                "travel solo",
            ],
            "statement": [
                "AI will replace most jobs",
                "remote work is more productive",
            ],
            "option1": ["rent", "buy a house", "work for a startup"],
            "option2": ["buy", "keep renting", "work for a corporation"],
        },
    },
    "creative_writing": {
        "templates": [
            "Write a poem about {topic}",
            "Tell me a story about {character}",
            "Create a haiku about {subject}",
            "Write a short essay on {topic}",
            "Compose a song about {theme}",
            "Write a limerick about {subject}",
            "Create a dialogue between {char1} and {char2}",
            "Write a metaphor for {concept}",
            "Describe {scene} poetically",
            "Write a brief story starting with {opening}",
        ],
        "variables": {
            "topic": ["nature", "love", "time", "hope", "change", "memory"],
            "character": [
                "a brave knight",
                "a curious robot",
                "a wise old tree",
                "a lost traveler",
            ],
            "subject": ["autumn", "the ocean", "moonlight", "silence", "friendship"],
            "theme": ["friendship", "adventure", "perseverance", "discovery"],
            "char1": ["a scientist", "a child", "an artist", "a philosopher"],
            "char2": ["an AI", "nature", "their past self", "a stranger"],
            "concept": ["time passing", "learning", "growth", "creativity"],
            "scene": ["a sunset", "a bustling market", "a quiet library", "a mountain peak"],
            "opening": [
                '"It was a dark and stormy night"',
                '"She never expected"',
                '"The door creaked open"',
            ],
        },
    },
    "math_knowledge": {
        "templates": [
            "What is pi?",
            "What is the Pythagorean theorem?",
            "What is the quadratic formula?",
            "Explain what a derivative is",
            "What is the formula for the area of a circle?",
            "What are prime numbers?",
            "What is the fibonacci sequence?",
            "Explain what a logarithm is",
            "What is the formula for compound interest?",
            "What does 'e' represent in mathematics?",
        ],
        "variables": {},
    },
    "history": {
        "templates": [
            "Who was {historical_figure}?",
            "What was the {historical_event}?",
            "When did the {period} period begin?",
            "What caused the {conflict}?",
            "How did {civilization} fall?",
            "What was life like in {era}?",
            "Who founded {organization}?",
            "What was the significance of {event}?",
            "How did {invention} change history?",
            "What were the main achievements of {empire}?",
        ],
        "variables": {
            "historical_figure": [
                "Napoleon Bonaparte",
                "Cleopatra",
                "Alexander the Great",
                "Genghis Khan",
            ],
            "historical_event": [
                "Industrial Revolution",
                "Renaissance",
                "French Revolution",
                "Cold War",
            ],
            "period": ["Renaissance", "Victorian", "Medieval", "Bronze Age", "Enlightenment"],
            "conflict": ["World War I", "American Civil War", "Hundred Years War", "Crusades"],
            "civilization": [
                "Roman Empire",
                "Maya civilization",
                "Ancient Egypt",
                "Byzantine Empire",
            ],
            "era": ["Ancient Greece", "Medieval Europe", "Renaissance Italy", "Victorian England"],
            "organization": ["United Nations", "NATO", "European Union", "OPEC"],
            "event": ["Magna Carta", "Declaration of Independence", "Berlin Wall fall"],
            "invention": ["printing press", "steam engine", "electricity", "the internet"],
            "empire": ["Roman Empire", "British Empire", "Ottoman Empire", "Mongol Empire"],
        },
    },
    "advice": {
        "templates": [
            "How can I improve my {skill}?",
            "What's a good way to learn {subject}?",
            "Any tips for {activity}?",
            "How do I get better at {skill}?",
            "What's the best approach to {task}?",
            "Can you suggest ways to {goal}?",
            "What should I focus on to {objective}?",
            "How do successful people {action}?",
            "What habits help with {goal}?",
            "What's important to know about {topic}?",
        ],
        "variables": {
            "skill": [
                "public speaking",
                "writing",
                "programming",
                "time management",
                "communication",
            ],
            "subject": [
                "a new language",
                "machine learning",
                "cooking",
                "photography",
                "music",
            ],
            "activity": [
                "job interviews",
                "studying for exams",
                "networking",
                "presentations",
            ],
            "task": [
                "solving complex problems",
                "making decisions",
                "managing stress",
                "staying motivated",
            ],
            "goal": [
                "be more productive",
                "stay healthy",
                "save money",
                "build confidence",
            ],
            "objective": [
                "master a skill",
                "advance my career",
                "improve relationships",
            ],
            "action": [
                "stay motivated",
                "manage their time",
                "handle failure",
                "make decisions",
            ],
            "topic": [
                "starting a business",
                "negotiation",
                "leadership",
                "personal finance",
            ],
        },
    },
}


def fill_template(template: str, variables: dict[str, list[str]]) -> str:
    """Fill in template placeholders with random values from variables."""
    result = template
    for key, values in variables.items():
        if f"{{{key}}}" in result:
            result = result.replace(f"{{{key}}}", random.choice(values))
    return result


def generate_tool_needed_samples(num_samples: int) -> list[dict[str, Any]]:
    """Generate samples where tool calling IS needed."""
    samples = []
    categories = list(TOOL_NEEDED_TEMPLATES.keys())

    for i in range(num_samples):
        category = random.choice(categories)
        cat_data = TOOL_NEEDED_TEMPLATES[category]
        template = random.choice(cat_data["templates"])
        message = fill_template(template, cat_data.get("variables", {}))

        sample = {
            "sample_id": f"tool_needed_{i:04d}",
            "message": message,
            "should_call_tool": True,
            "direct_answer": None,
            "context": {},
            "category": category,
            "reasoning_chain": [
                "This query requires real-time or dynamic information",
                f"Category: {category}",
                "Tool invocation is necessary to provide accurate response",
            ],
        }
        samples.append(sample)

    return samples


def generate_no_tool_samples(num_samples: int) -> list[dict[str, Any]]:
    """Generate samples where tool calling is NOT needed."""
    samples = []
    categories = list(NO_TOOL_TEMPLATES.keys())

    # Direct answers for different categories
    direct_answer_templates = {
        "factual_knowledge": "This is factual knowledge that can be answered directly.",
        "definitions": "The definition can be provided from general knowledge.",
        "explanations": "This concept can be explained without external tools.",
        "conversational": "This is a conversational message that doesn't require tools.",
        "opinions": "This is a request for opinion/analysis that can be answered directly.",
        "creative_writing": "This is a creative writing request that can be generated directly.",
        "math_knowledge": "This is mathematical knowledge that can be explained directly.",
        "history": "This is historical information that can be answered from knowledge.",
        "advice": "This is a request for advice that can be provided directly.",
    }

    for i in range(num_samples):
        category = random.choice(categories)
        cat_data = NO_TOOL_TEMPLATES[category]
        template = random.choice(cat_data["templates"])
        message = fill_template(template, cat_data.get("variables", {}))

        sample = {
            "sample_id": f"no_tool_{i:04d}",
            "message": message,
            "should_call_tool": False,
            "direct_answer": direct_answer_templates.get(category, "Can be answered directly."),
            "context": {},
            "category": category,
            "reasoning_chain": [
                "This query can be answered from existing knowledge",
                f"Category: {category}",
                "No tool invocation needed - direct response is appropriate",
            ],
        }
        samples.append(sample)

    return samples


def generate_dataset(
    output_dir: Path,
    num_tool_needed: int = 500,
    num_no_tool: int = 500,
) -> dict[str, Any]:
    """
    Generate complete timing judgment dataset.

    Args:
        output_dir: Directory to save data files
        num_tool_needed: Number of tool-needed samples
        num_no_tool: Number of no-tool-needed samples

    Returns:
        Statistics about generated dataset
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate samples
    tool_needed = generate_tool_needed_samples(num_tool_needed)
    no_tool = generate_no_tool_samples(num_no_tool)

    # Combine and shuffle
    all_samples = tool_needed + no_tool
    random.shuffle(all_samples)

    # Split into train/dev/test (70/15/15)
    n = len(all_samples)
    train_end = int(n * 0.7)
    dev_end = int(n * 0.85)

    splits = {
        "train": all_samples[:train_end],
        "dev": all_samples[train_end:dev_end],
        "test": all_samples[dev_end:],
    }

    # Write JSONL files
    stats = {"total": n, "splits": {}}
    for split_name, samples in splits.items():
        output_file = output_dir / f"{split_name}.jsonl"
        with open(output_file, "w", encoding="utf-8") as f:
            for sample in samples:
                f.write(json.dumps(sample, ensure_ascii=False) + "\n")

        # Compute stats for this split
        tool_count = sum(1 for s in samples if s["should_call_tool"])
        no_tool_count = len(samples) - tool_count

        stats["splits"][split_name] = {
            "total": len(samples),
            "tool_needed": tool_count,
            "no_tool": no_tool_count,
            "tool_ratio": tool_count / len(samples) if samples else 0,
            "file": str(output_file),
        }

        print(
            f"  {split_name}: {len(samples)} samples ({tool_count} tool, {no_tool_count} no-tool)"
        )

    # Write metadata
    metadata = {
        "description": "Timing judgment benchmark dataset for SAGE Agent Benchmark",
        "version": "1.0.0",
        "total_samples": n,
        "splits": stats["splits"],
        "categories": {
            "tool_needed": list(TOOL_NEEDED_TEMPLATES.keys()),
            "no_tool": list(NO_TOOL_TEMPLATES.keys()),
        },
        "fields": {
            "sample_id": "Unique identifier",
            "message": "User message text",
            "should_call_tool": "Boolean ground truth",
            "direct_answer": "Optional answer if no tool needed",
            "context": "Optional conversation context",
            "category": "Category for analysis",
            "reasoning_chain": "Reasoning steps for ground truth",
        },
    }

    metadata_file = output_dir / "metadata.json"
    with open(metadata_file, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    print(f"\nMetadata saved to: {metadata_file}")

    return stats


def main():
    parser = argparse.ArgumentParser(description="Generate timing judgment dataset")
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help=f"Output directory for dataset files (default: {DEFAULT_OUTPUT_DIR})",
    )
    parser.add_argument(
        "--num-tool-needed",
        type=int,
        default=500,
        help="Number of samples where tool is needed",
    )
    parser.add_argument(
        "--num-no-tool",
        type=int,
        default=500,
        help="Number of samples where tool is not needed",
    )

    args = parser.parse_args()

    # Use .sage/benchmark/ by default
    output_path = Path(args.output) if args.output else DEFAULT_OUTPUT_DIR

    print("Generating timing judgment dataset...")
    print(f"  Output: {output_path}")
    print(f"  Tool-needed samples: {args.num_tool_needed}")
    print(f"  No-tool samples: {args.num_no_tool}")
    print()

    stats = generate_dataset(
        output_path,
        num_tool_needed=args.num_tool_needed,
        num_no_tool=args.num_no_tool,
    )

    print("\nDataset generation complete!")
    print(f"Total samples: {stats['total']}")


if __name__ == "__main__":
    main()

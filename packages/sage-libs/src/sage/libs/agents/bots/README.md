# SAGE Agent Bots

**Layer**: L3 (Core - Algorithm Library)\
**Purpose**: Pre-built agent implementations

## Overview

This module provides ready-to-use agent bot implementations for common tasks:

- Question answering
- Question generation
- Information retrieval
- Output critique and evaluation

## Components

### Bots

- **answer_bot.py**: AnswerBot - Specialized in answering questions
- **question_bot.py**: QuestionBot - Generates clarifying questions
- **searcher_bot.py**: SearcherBot - Performs information retrieval
- **critic_bot.py**: CriticBot - Evaluates and critiques outputs

## Usage

```python
from sage.libs.agents.bots import AnswerBot, QuestionBot

# Create bot instances
answer_bot = AnswerBot()
question_bot = QuestionBot()

# Use bots
answer = answer_bot.answer(question, context)
questions = question_bot.generate_questions(topic)
```

## Design Principles

1. **Specialization**: Each bot focuses on a specific task
1. **Reusability**: Bots can be composed into workflows
1. **Configurability**: Bots accept configuration parameters
1. **Extensibility**: Easy to create new bot types

## Bot Patterns

### AnswerBot

- Takes questions and context
- Generates accurate answers
- Handles follow-up questions

### QuestionBot

- Generates clarifying questions
- Identifies information gaps
- Improves conversation quality

### SearcherBot

- Performs information retrieval
- Ranks search results
- Extracts relevant information

### CriticBot

- Evaluates output quality
- Identifies issues and errors
- Suggests improvements

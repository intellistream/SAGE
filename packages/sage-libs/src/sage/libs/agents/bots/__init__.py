"""
SAGE Agent Bots - Pre-built Agent Implementations

Layer: L3 (Core - Algorithm Library)

This module provides pre-built, ready-to-use agent bot implementations
for common tasks and workflows.

Available Bots:
- AnswerBot: Specialized in answering questions
- QuestionBot: Generates clarifying questions
- SearcherBot: Performs information retrieval
- CriticBot: Evaluates and critiques outputs
"""

from .answer_bot import *
from .critic_bot import *
from .question_bot import *
from .searcher_bot import *

__all__ = [
    # Re-export from submodules
    # Will be populated as modules are standardized
]

__version__ = "0.1.0"

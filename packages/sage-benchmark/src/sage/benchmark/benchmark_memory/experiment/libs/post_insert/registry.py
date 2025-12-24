"""
PostInsert Action Registry
===========================

Central registry for all PostInsert action strategies.
"""

from .base import BasePostInsertAction
from .crud import CRUDAction
from .distillation import DistillationAction
from .enhance.profile_extraction import ProfileExtractionAction
from .forgetting import ForgettingAction
from .link_evolution import LinkEvolutionAction
from .migrate import MigrateAction
from .none_action import NoneAction


class PostInsertActionRegistry:
    """Registry for PostInsert action strategies.

    This registry maintains a mapping from action names to action classes,
    enabling dynamic action selection based on configuration.

    Usage:
        >>> registry = PostInsertActionRegistry()
        >>> action_class = registry.get("distillation")
        >>> action = action_class(config)
    """

    _actions: dict[str, type[BasePostInsertAction]] = {}

    @classmethod
    def register(cls, name: str, action_class: type[BasePostInsertAction]) -> None:
        """Register an action class.

        Args:
            name: Action name (e.g., "none", "distillation")
            action_class: Action class (must inherit from BasePostInsertAction)

        Raises:
            ValueError: If action_class is not a subclass of BasePostInsertAction
        """
        if not issubclass(action_class, BasePostInsertAction):
            raise ValueError(
                f"Action class must inherit from BasePostInsertAction, got {action_class}"
            )

        cls._actions[name] = action_class

    @classmethod
    def get(cls, name: str) -> type[BasePostInsertAction]:
        """Get action class by name.

        Args:
            name: Action name

        Returns:
            Action class

        Raises:
            ValueError: If action name is not registered
        """
        if name not in cls._actions:
            available = ", ".join(cls._actions.keys())
            raise ValueError(f"Unknown action: {name}. Available actions: {available}")

        return cls._actions[name]

    @classmethod
    def list_actions(cls) -> list[str]:
        """List all registered action names.

        Returns:
            List of action names
        """
        return list(cls._actions.keys())

    @classmethod
    def is_registered(cls, name: str) -> bool:
        """Check if an action is registered.

        Args:
            name: Action name

        Returns:
            True if registered, False otherwise
        """
        return name in cls._actions


# ========================= Register All Actions =========================

# [A] Passthrough - No post-processing
PostInsertActionRegistry.register("none", NoneAction)

# [B] Distillation - Memory merging (TiM, MemGPT, SeCom)
PostInsertActionRegistry.register("distillation", DistillationAction)

# [C] CRUD - Decision making (Mem0, Mem0ᵍ)
PostInsertActionRegistry.register("crud", CRUDAction)

# [D] Link Evolution - Graph edge creation (A-Mem, HippoRAG)
PostInsertActionRegistry.register("link_evolution", LinkEvolutionAction)

# [E] Migrate - Layer migration (MemoryOS)
PostInsertActionRegistry.register("migrate", MigrateAction)

# [F] Forgetting - Active forgetting (MemoryBank, MemoryOS, LD-Agent)
PostInsertActionRegistry.register("forgetting", ForgettingAction)

# [G] Profile Extraction - Extract user profile and knowledge (MemoryOS)
PostInsertActionRegistry.register("enhance.profile_extraction", ProfileExtractionAction)


# ========================= Helper Functions =========================


def get_action(name: str, config: dict) -> BasePostInsertAction:
    """Convenience function to get and instantiate an action.

    Args:
        name: Action name
        config: Action configuration

    Returns:
        Instantiated action object

    Example:
        >>> action = get_action("distillation", {"similarity_threshold": 0.9})
        >>> result = action.execute(input_data, service, llm)
    """
    action_class = PostInsertActionRegistry.get(name)
    return action_class(config)

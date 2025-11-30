"""
Registry for tool selector strategies.

Provides registration, lookup, and factory creation of selectors.
"""

import logging
from typing import Any, Optional

from .base import BaseToolSelector, SelectorResources
from .schemas import SelectorConfig, create_selector_config

logger = logging.getLogger(__name__)


class SelectorRegistry:
    """
    Registry for tool selector strategies.

    Supports registration, lookup, and factory creation of selectors.
    """

    _instance: Optional["SelectorRegistry"] = None
    _selectors: dict[str, type[BaseToolSelector]] = {}

    def __init__(self):
        """Initialize registry."""
        self._selectors = {}
        self._instances: dict[str, BaseToolSelector] = {}

    @classmethod
    def get_instance(cls) -> "SelectorRegistry":
        """Get singleton registry instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def register(self, name: str, selector_class: type[BaseToolSelector]) -> None:
        """
        Register a selector class.

        Args:
            name: Selector strategy name
            selector_class: Selector class to register
        """
        if name in self._selectors:
            logger.warning(f"Overwriting existing selector: {name}")

        self._selectors[name] = selector_class
        logger.info(f"Registered selector: {name}")

    def get_class(self, name: str) -> Optional[type[BaseToolSelector]]:
        """
        Get selector class by name.

        Args:
            name: Selector strategy name

        Returns:
            Selector class or None if not found
        """
        return self._selectors.get(name)

    def get(
        self,
        name: str,
        config: Optional[SelectorConfig] = None,
        resources: Optional[SelectorResources] = None,
        cache: bool = True,
    ) -> BaseToolSelector:
        """
        Get or create selector instance.

        Args:
            name: Selector strategy name
            config: Optional selector configuration
            resources: Optional resources (required for new instances)
            cache: Whether to cache and reuse instances

        Returns:
            Selector instance

        Raises:
            ValueError: If selector not registered or resources missing
        """
        # Check cache
        if cache and name in self._instances:
            return self._instances[name]

        # Get class
        selector_class = self.get_class(name)
        if selector_class is None:
            raise ValueError(f"Unknown selector: {name}. Available: {list(self._selectors.keys())}")

        # Create config if needed
        if config is None:
            config = create_selector_config({"name": name})

        # Validate resources
        if resources is None:
            raise ValueError(f"Resources required to create selector: {name}")

        # Create instance
        instance = selector_class.from_config(config, resources)

        # Cache if requested
        if cache:
            self._instances[name] = instance

        return instance

    def create_from_config(
        self, config_dict: dict[str, Any], resources: SelectorResources
    ) -> BaseToolSelector:
        """
        Create selector from configuration dictionary.

        Args:
            config_dict: Configuration dictionary
            resources: Shared resources

        Returns:
            Initialized selector instance
        """
        config = create_selector_config(config_dict)
        return self.get(config.name, config, resources, cache=False)

    def list_selectors(self) -> list:
        """List all registered selector names."""
        return list(self._selectors.keys())

    def clear_cache(self) -> None:
        """Clear cached selector instances."""
        self._instances.clear()
        logger.info("Cleared selector instance cache")


# Global registry instance
_registry = SelectorRegistry.get_instance()


def register_selector(name: str, selector_class: type[BaseToolSelector]) -> None:
    """
    Register a selector class globally.

    Args:
        name: Selector strategy name
        selector_class: Selector class to register
    """
    _registry.register(name, selector_class)


def get_selector(
    name: str,
    config: Optional[SelectorConfig] = None,
    resources: Optional[SelectorResources] = None,
) -> BaseToolSelector:
    """
    Get selector instance from global registry.

    Args:
        name: Selector strategy name
        config: Optional selector configuration
        resources: Optional resources

    Returns:
        Selector instance
    """
    return _registry.get(name, config, resources)


def create_selector_from_config(
    config_dict: dict[str, Any], resources: SelectorResources
) -> BaseToolSelector:
    """
    Create selector from config dictionary using global registry.

    Args:
        config_dict: Configuration dictionary
        resources: Shared resources

    Returns:
        Initialized selector instance
    """
    return _registry.create_from_config(config_dict, resources)

from abc import abstractmethod
from typing import Any, Optional, Union, Hashable
from sage.core.api.function.base_function import BaseFunction


class KeyByFunction(BaseFunction):
    """
    KeyByFunction is a specialized function for KeyBy operations.
    It extracts partition keys from input data for downstream routing.
    
    The function should return a hashable value that will be used as
    the partition key for routing data to downstream operators.
    
    Example usage:
        class UserIdExtractor(KeyByFunction):
            def execute(self, data):
                return data.user_id
        
        class CategoryExtractor(KeyByFunction):
            def execute(self, data):
                return data.category.lower()
        
        class CompositeKeyExtractor(KeyByFunction):
            def execute(self, data):
                return f"{data.user_id}_{data.session_id}"
    """
    

    @abstractmethod
    def execute(self, data: Any) -> Hashable:
        """
        Abstract method to extract partition key from input data.
        
        Args:
            data: Input data from upstream operator
            
        Returns:
            Hashable: Partition key that will be used for routing.
                     Must be hashable (str, int, tuple, etc.)
                     
        Raises:
            KeyError: If required field is missing from data
            ValueError: If extracted key is not hashable
            
        Note:
            - The returned key will be used with hash() function for partitioning
            - None values are allowed but will route to a default partition
            - Complex objects should be converted to simple hashable types
        """
        pass

    def validate_key(self, key: Any) -> bool:
        """
        Validate if the extracted key is suitable for partitioning.
        
        Args:
            key: The extracted key to validate
            
        Returns:
            bool: True if key is valid for partitioning
            
        Note:
            This method can be overridden for custom validation logic.
        """
        try:
            # Test if key is hashable
            hash(key)
            return True
        except TypeError:
            self.logger.warning(f"Extracted key {key} is not hashable")
            return False

    def extract_with_validation(self, data: Any) -> Hashable:
        """
        Extract key with built-in validation.
        
        Args:
            data: Input data
            
        Returns:
            Hashable: Validated partition key
            
        Raises:
            ValueError: If extracted key is not valid for partitioning
        """
        try:
            key = self.execute(data)
            
            if not self.validate_key(key):
                raise ValueError(f"Invalid partition key: {key} (not hashable)")
                
            self.logger.debug(f"Extracted and validated key: {key}")
            return key
            
        except Exception as e:
            self.logger.error(f"Error extracting partition key: {e}", exc_info=True)
            raise

    def __call__(self, data: Any) -> Hashable:
        """
        Convenience method to make function callable.
        
        Args:
            data: Input data
            
        Returns:
            Hashable: Partition key
        """
        return self.extract_with_validation(data)


class FieldKeyByFunction(KeyByFunction):
    """
    Convenience class for simple field-based key extraction.
    
    Example:
        # Extract user_id field
        class UserIdExtractor(FieldKeyByFunction):
            field_name = "user_id"
        
        # Extract nested field
        class RegionExtractor(FieldKeyByFunction):
            field_name = "location.region"
    """
    
    field_name: str = None  # To be set by subclasses
    
    def __init__(self, field_name: str = None, **kwargs):
        super().__init__(**kwargs)
        if field_name:
            self.field_name = field_name
        if not self.field_name:
            raise ValueError("field_name must be specified")
        self.logger.debug(f"FieldKeyByFunction initialized for field: {self.field_name}")

    def execute(self, data: Any) -> Hashable:
        """
        Extract field value from data object.
        
        Args:
            data: Input data object
            
        Returns:
            Hashable: Field value
            
        Raises:
            KeyError: If field is not found
            AttributeError: If data doesn't support field access
        """
        try:
            # Handle nested field access (e.g., "location.region")
            if '.' in self.field_name:
                value = data
                for field_part in self.field_name.split('.'):
                    if hasattr(value, field_part):
                        value = getattr(value, field_part)
                    elif hasattr(value, '__getitem__'):
                        value = value[field_part]
                    else:
                        raise KeyError(f"Field '{field_part}' not found")
                return value
            else:
                # Simple field access
                if hasattr(data, self.field_name):
                    return getattr(data, self.field_name)
                elif hasattr(data, '__getitem__'):
                    return data[self.field_name]
                else:
                    raise KeyError(f"Field '{self.field_name}' not found")
                    
        except Exception as e:
            self.logger.error(f"Failed to extract field '{self.field_name}': {e}")
            raise KeyError(f"Field '{self.field_name}' not accessible: {e}")



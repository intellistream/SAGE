"""
Utility functions for the model service.
"""

import logging
import time
from functools import wraps

logger = logging.getLogger(__name__)


def retry_decorator(max_retries=3, delay=1, backoff=2):
    """Decorator for retrying functions that might fail

    Args:
        max_retries (int): Maximum number of retries
        delay (int): Initial delay between retries in seconds
        backoff (int): Backoff multiplier for subsequent retries
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            current_delay = delay
            last_exception = None

            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    logger.warning(
                        f"Error in {func.__name__}: {str(e)}. Retry {retries + 1}/{max_retries}"
                    )

                retries += 1
                if retries < max_retries:
                    logger.info(f"Retrying in {current_delay} seconds...")
                    time.sleep(current_delay)
                    current_delay *= backoff

            logger.error(f"Function {func.__name__} failed after {max_retries} retries")
            raise last_exception

        return wrapper

    return decorator

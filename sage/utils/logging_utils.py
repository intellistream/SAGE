import logging

def configure_logging(level: int = logging.INFO) -> None:
    """
    Prints lines like:
      /path/to/module.py:47: ERROR: File not found: …
    which IDEs detect as clickable links.
    """
    fmt = "%(pathname)s:%(lineno)d: %(levelname)s: %(message)s"
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(fmt))
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)

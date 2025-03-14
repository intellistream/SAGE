import logging


def configure_logging(level=logging.INFO, log_file=None):
    """
    Configures logging for the application.

    :param level: Logging level (default: logging.INFO)
    :param log_file: Path to a log file to write logs (optional)
    """
    handlers = [logging.StreamHandler()]
    if log_file:
        handlers.append(logging.FileHandler(log_file))

    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=handlers,
    )


def get_logger(name):
    """
    Creates a logger instance with the specified name.

    :param name: Name for the logger.
    :return: Configured logger instance.
    """
    return logging.getLogger(name)
logger = logging.getLogger("sage")
logger.propagate = False  # prevent log message send to root loggger
# Let the main application configure the handlers
logger.setLevel(logging.INFO)

# Set httpx logging level to WARNING
logging.getLogger("httpx").setLevel(logging.WARNING)
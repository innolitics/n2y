import logging
import os


def filter_log(record: logging.LogRecord) -> logging.LogRecord:
    """Filter log records."""
    record.pathname = record.pathname.replace(os.getcwd() + "/", "")
    return record


FORMATTER = logging.Formatter(
    "%(asctime)s - %(levelname)s (%(pathname)s::%(funcName)s::%(lineno)d): %(message)s"
)
HANDLER = logging.StreamHandler()
HANDLER.setFormatter(FORMATTER)
HANDLER.addFilter(filter_log)
logging.basicConfig(level=logging.INFO, handlers=[HANDLER])
logger: logging.Logger = logging.getLogger(__name__)

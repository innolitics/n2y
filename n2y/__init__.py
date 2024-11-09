import logging
import os


def log_filter(record: logging.LogRecord) -> logging.LogRecord:
    record.pathname = record.pathname.replace(os.getcwd() + "/", "")
    return record


LOG_FORMATTER = logging.Formatter(
    "%(asctime)s - %(levelname)s (%(pathname)s::%(funcName)s::%(lineno)d): %(message)s"
)
LOG_HANDLER = logging.StreamHandler()
LOG_HANDLER.setLevel(logging.INFO)
LOG_HANDLER.setFormatter(LOG_FORMATTER)
LOG_HANDLER.addFilter(log_filter)
LOG = logging.getLogger(__name__)
LOG.addHandler(LOG_HANDLER)

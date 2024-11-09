import logging
import os


def filter_log(record: logging.LogRecord) -> logging.LogRecord:
    record.pathname = record.pathname.replace(os.getcwd() + "/", "")
    return record


FORMATTER = logging.Formatter(
    "%(asctime)s - %(levelname)s (%(pathname)s::%(funcName)s::%(lineno)d): %(message)s"
)
HANDLER = logging.StreamHandler()
HANDLER.setLevel(logging.INFO)
HANDLER.setFormatter(FORMATTER)
HANDLER.addFilter(filter_log)
LOG = logging.getLogger(__name__)
LOG.addHandler(HANDLER)

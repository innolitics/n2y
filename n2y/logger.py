import logging

FORMATTER = logging.Formatter(
    "%(asctime)s - %(levelname)s - n2y.%(module)s: %(message)s"
)
HANDLER = logging.StreamHandler()
HANDLER.setFormatter(FORMATTER)
logging.basicConfig(level=logging.INFO, handlers=[HANDLER])
logger: logging.Logger = logging.getLogger(__name__)


def update_logger(new_logger: logging.Logger):
    global logger
    logger = new_logger

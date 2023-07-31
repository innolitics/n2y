import logging

FORMATTER = logging.Formatter('%(asctime)s - %(levelname)s - n2y.%(module)s: %(message)s')
HANDLER = logging.StreamHandler()
HANDLER.setFormatter(FORMATTER)
logger: logging.Logger = logging.getLogger(__name__)
logger.addHandler(HANDLER)

def update_logger(new_logger: logging.Logger):
    global logger
    logger = new_logger
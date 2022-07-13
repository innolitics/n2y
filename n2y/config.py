import json
import logging

from n2y.utils import strip_hyphens


logger = logging.getLogger(__name__)


def database_config_json_to_dict(config_json):
    try:
        config = json.loads(config_json)
    except json.JSONDecodeError as exc:
        logger.error("Error parsing the data config JSON: %s", exc.msg)
        return None
    if not validate_database_config(config):
        return None
    return config


def validate_database_config(config):
    try:
        for database_id, config_values in config.items():
            if not _valid_id(database_id):
                logger.error("Invalid database id in database config: %s", database_id)
                return False
            for key, values in config_values.items():
                if key not in ["sorts", "filter"]:
                    logger.error("Invalid key in database config: %s", key)
                    return False
                if not isinstance(values, dict) and not isinstance(values, list):
                    logger.error(
                        "Invalid value of type '%s' for key '%s' in database config, "
                        "expected dict or list", type(values), key,
                    )
                    return False
    except AttributeError:
        return False
    return True


def _valid_id(notion_id):
    return len(strip_hyphens(notion_id)) == 32

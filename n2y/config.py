import json
import logging
import copy

import yaml

from n2y.utils import strip_hyphens


logger = logging.getLogger(__name__)


MASTER_DEFAULTS = {
    "id_property": None,
    "content_property": None,
    "url_property": None,
    "filename_property": None,
    "plugins": [],
    "filter": None,
}


def load_config(path):
    try:
        with open(path, "r") as config_file:
            config = yaml.safe_load(config_file)
    except yaml.YAMLError as exc:
        logger.error("Error parsing the config file: %s", exc)
        return None
    except FileNotFoundError:
        logger.error("The config file '%s' does not exist", path)
        return None
    merged_exports = merge_config(
        config.get("exports", []),
        MASTER_DEFAULTS,
        config.get("export_defaults", {}),
    )
    config["exports"] = merged_exports
    # TODO: update how validate_database_config works to handle the new format
    # TODO: validate the database config using the updated validate_database_config
    return config


def merge_config(config_items, master_defaults, defaults):
    """
    For each config item, merge in both the user provided defaults and the
    builtin master defaults for each key value pair."
    """
    merged_config_items = []
    for config_item in config_items:
        master_defaults_copy = copy.deepcopy(master_defaults)
        defaults_copy = copy.deepcopy(defaults)
        config_item_copy = copy.deepcopy(config_item)
        merged_config_item = {**master_defaults_copy, **defaults_copy, **config_item_copy}
        merged_config_items.append(merged_config_item)
    return merged_config_items


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

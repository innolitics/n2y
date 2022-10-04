import logging
import copy

import yaml

from n2y.utils import strip_hyphens


logger = logging.getLogger(__name__)


DEFAULTS = {
    "media_root": "media",
    "media_url": "./media/",
}


EXPORT_DEFAULTS = {
    "id_property": None,
    "content_property": None,
    "url_property": None,
    "notion_filter": [],
    "notion_sorts": [],
    "pandoc_format": "gfm+tex_math_dollars+raw_attribute",
    "pandoc_options": [
        '--wrap', 'none',  # don't hard line-wrap
        '--eol', 'lf',  # use linux-style line endings
    ],
    "plugins": [],
    "property_map": {},
}


def load_config(path):
    config = _load_config_from_yaml(path)
    if config is None:
        return None

    defaults_copy = copy.deepcopy(DEFAULTS)
    config = {**defaults_copy, **config}

    merged_exports = merge_config(
        config.get("exports", []),
        EXPORT_DEFAULTS,
        config.get("export_defaults", {}),
    )
    config["exports"] = merged_exports
    return config


def _load_config_from_yaml(path):
    try:
        with open(path, "r") as config_file:
            config = yaml.safe_load(config_file)
    except yaml.YAMLError as exc:
        logger.error("Error parsing the config file: %s", exc)
        return None
    except FileNotFoundError:
        logger.error("The config file '%s' does not exist", path)
        return None
    if not validate_config(config):
        logger.error("Invalid config file: %s", path)
        return None
    return config


def merge_config(config_items, builtin_defaults, defaults):
    """
    For each config item, merge in both the user provided defaults and the
    builtin defaults for each key value pair."
    """
    merged_config_items = []
    for config_item in config_items:
        master_defaults_copy = copy.deepcopy(builtin_defaults)
        defaults_copy = copy.deepcopy(defaults)
        config_item_copy = copy.deepcopy(config_item)
        merged_config_item = {**master_defaults_copy, **defaults_copy, **config_item_copy}
        merged_config_items.append(merged_config_item)
    return merged_config_items


def validate_config(config):
    if "exports" not in config:
        logger.error("Config missing the 'exports' key")
        return False
    if not isinstance(config["exports"], list) and len(config["exports"]) > 0:
        logger.error("Config 'exports' key must be a non-empty list")
        return False
    for export in config["exports"]:
        if not _validate_config_item(export):
            return False
    # TODO: validate the export defaults key
    return True


def _validate_config_item(config_item):
    if "id" not in config_item:
        logger.error("Export config item missing the 'id' key")
        return False
    if not _valid_id(config_item["id"]):
        logger.error("Invalid id in export config item: %s", config_item["id"])
    if "node_type" not in config_item:
        logger.error("Export config item missing the 'node_type' key")
        return False
    if config_item["node_type"] not in ["page", "database_as_yaml", "database_as_files"]:
        logger.error("Invalid node_type in export config item: %s", config_item["node_type"])
        return False
    if config_item["node_type"] == "database_as_files" and "filename_property" not in config_item:
        logger.error("Missing the 'filename_property' key when node_type is 'database_as_files'")
        return False
    if "output" not in config_item:
        logger.error("Export config item missing the 'output' key")
        return False
    if "notion_filter" in config_item:
        if not _valid_notion_filter(config_item["notion_filter"]):
            return False
    if "notion_sorts" in config_item:
        if not _valid_notion_sort(config_item["notion_sorts"]):
            return False
    # TODO: validate pandoc_formation
    # TODO: validate pandoc_options
    # TODO: property map
    return True


def _valid_notion_filter(notion_filter):
    if not (isinstance(notion_filter, list) or isinstance(notion_filter, dict)):
        logger.error("notion_filter must be a list or dict")
        return False
    # TODO validate keys and values
    return True


def _valid_notion_sort(notion_sorts):
    if not (isinstance(notion_sorts, list) or isinstance(notion_sorts, dict)):
        logger.error("notion_sorts must be a list or dict")
        return False
    # TODO validate keys and values
    return True


def _valid_id(notion_id):
    return len(strip_hyphens(notion_id)) == 32

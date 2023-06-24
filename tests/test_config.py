import copy
import yaml

from n2y.config import (
    valid_notion_id, merge_config, load_config, _valid_notion_filter,
    _validate_config_item, EXPORT_DEFAULTS
)
from n2y.notion_mocks import mock_id


def mock_config_item(node_type):
    config_item = copy.deepcopy(EXPORT_DEFAULTS)
    config_item["id"] = mock_id()
    config_item["node_type"] = node_type
    return config_item


def test_load_config_basic(tmp_path):
    # use a temporary file to test the config loading
    config_path = tmp_path / "config.yaml"
    export_id = mock_id()
    with open(config_path, "w") as f:
        f.write(yaml.dump({
            "media_root": "media",
            "media_url": "https://example.com/media",
            "export_defaults": {
                "id_property": "id",
                "url_property": "url",
            },
            "exports": [
                {
                    "id": export_id,
                    "node_type": "page",
                    "output": "output.md",
                    "pandoc_format": "gfm",
                }
            ]
        }))
    config = load_config(config_path)
    assert config is not None, "The config is invalid"
    merged_export = config["exports"][0]
    assert merged_export["id"] == export_id
    assert merged_export["node_type"] == "page"
    assert merged_export["id_property"] == "id"
    assert merged_export["url_property"] == "url"
    assert merged_export["pandoc_format"] == "gfm"


def test_merge_config_no_defaults():
    master_defaults = {"a": "1"}
    defaults = {}
    config_items = [
        {"b": "1"},
        {"b": "2", "a": "2"},
    ]
    assert merge_config(config_items, master_defaults, defaults) == [
        {"a": "1", "b": "1"},
        {"b": "2", "a": "2"},
    ]


def test_merge_config_defaults():
    master_defaults = {"a": "1", "b": "1"}
    defaults = {"a": "3"}
    config_items = [
        {},
        {"a": "2"},
        {"b": "2"},
    ]
    assert merge_config(config_items, master_defaults, defaults) == [
        {"a": "3", "b": "1"},
        {"a": "2", "b": "1"},
        {"a": "3", "b": "2"},
    ]


def test_valid_id_valid():
    assert valid_notion_id(mock_id())


def test_valid_id_invalid():
    assert not valid_notion_id(mock_id() + 'a')


def test_valid_id_invalid_due_to_special():
    bad_id = 'https://' + mock_id()[8:]
    assert not valid_notion_id(bad_id)


def test_valid_notion_filter_simple():
    assert _valid_notion_filter({
        "property": "title",
        "direction": "ascending",
    })


def test_valid_notion_filter_complex():
    assert _valid_notion_filter([{
        "property": "title",
        "direction": "ascending",
    }])


def test_valid_config_item_missing_id():
    config_item = mock_config_item("page")
    del config_item["id"]
    assert not _validate_config_item(config_item)


def test_valid_config_item_missing_node_type():
    config_item = mock_config_item("page")
    del config_item["node_type"]
    assert not _validate_config_item(config_item)


def test_valid_config_item_invalid_node_type():
    config_item = mock_config_item("page")
    config_item["node_type"] = "invalid"
    assert not _validate_config_item(config_item)


def test_valid_config_item_missing_filename_template():
    config_item = mock_config_item("database_as_files")
    assert not _validate_config_item(config_item)


def test_valid_config_item_malformed_filename_template():
    config_item = mock_config_item("database_as_files")
    config_item["filename_template"] = "{"
    assert not _validate_config_item(config_item)

import yaml

from n2y.config import validate_database_config, merge_config, load_config
from n2y.notion_mocks import mock_id


def test_load_config_basic(tmp_path):
    # use a temporary file to test the config loading
    config_path = tmp_path / "config.yaml"
    export_id = mock_id()
    with open(config_path, "w") as f:
        f.write(yaml.dump({
            "export_defaults": {
                "id_property": "id",
                "url_property": "url",
            },
            "exports": [
                {
                    "id": export_id,
                    "pandoc_format": "gfm",
                }
            ]
        }))
    config = load_config(config_path)
    merged_export = config["exports"][0]
    assert merged_export["id"] == export_id
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


def test_validate_database_config_empty():
    assert validate_database_config({})


def test_validate_database_config_no_props():
    assert validate_database_config({
        mock_id(): {},
    })


def test_validate_database_config_invalid_id():
    invalid_id = mock_id() + 'a'
    assert not validate_database_config({
        invalid_id: {},
    })


def test_validate_database_config_invalid_props():
    assert not validate_database_config({
        mock_id(): {'invalid': 'thing'},
    })


def test_validate_database_config_invalid_value():
    assert not validate_database_config({
        mock_id(): {'filter': 'invalid'},
    })


def test_validate_database_config_valid_dict():
    assert validate_database_config({
        mock_id(): {'filter': {}},
    })


def test_validate_database_config_valid_list():
    assert validate_database_config({
        mock_id(): {'filter': []},
    })

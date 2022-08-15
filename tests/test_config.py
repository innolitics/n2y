from n2y.config import validate_database_config
from n2y.notion_mocks import mock_id


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

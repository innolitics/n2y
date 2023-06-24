import pytest
from n2y import notion

from n2y.notion_mocks import (
    mock_formula_property_value, mock_person_user, mock_relation_value,
    mock_rich_text, mock_property_value, mock_rich_text_array,
    mock_rollup_property_value, mock_select_option, mock_user,
)


def process_property_value(notion_data):
    client = notion.Client('')
    property_value = client.wrap_notion_property_value(notion_data, None)
    return property_value.to_value('gfm')


def test_title():
    notion_data = mock_property_value('title', [mock_rich_text('text')])
    assert process_property_value(notion_data) == 'text'


def test_rich_text_empty():
    notion_data = mock_property_value('rich_text', [])
    assert process_property_value(notion_data) == ''


def test_rich_text_annotated():
    notion_data = mock_property_value('rich_text', mock_rich_text_array([
        ('Hello', ['bold']), (' ', []), ('Goodbye', 'italic')
    ]))
    assert process_property_value(notion_data) == '**Hello** *Goodbye*\n'


def test_number_empty():
    notion_data = mock_property_value('number', None)
    assert process_property_value(notion_data) is None


def test_number_non_empty():
    notion_data = mock_property_value('number', 3)
    assert process_property_value(notion_data) == 3


def test_select_empty():
    notion_data = mock_property_value('select', None)
    assert process_property_value(notion_data) is None


def test_select_non_empty():
    notion_data = mock_property_value('select', mock_select_option('A'))
    assert process_property_value(notion_data) == 'A'


def test_multi_select_empty():
    notion_data = mock_property_value('multi_select', [])
    assert process_property_value(notion_data) == []


def test_multi_select_non_empty():
    notion_data = mock_property_value('multi_select', [
        mock_select_option('A'),
        mock_select_option('B'),
    ])
    assert process_property_value(notion_data) == ['A', 'B']


def test_date_empty():
    notion_data = mock_property_value('date', None)
    assert process_property_value(notion_data) is None


def test_date_start_only():
    notion_data = mock_property_value('date', {'start': '2022-05-11'})
    assert process_property_value(notion_data) == '2022-05-11'


def test_date_start_and_end():
    notion_data = mock_property_value('date', {'start': '2022-05-11', 'end': '2022-05-12'})
    assert process_property_value(notion_data) == ['2022-05-11', '2022-05-12']


def test_people_empty():
    notion_data = mock_property_value('people', [])
    assert process_property_value(notion_data) == []


def test_people_minimal_user():
    notion_data = mock_property_value('people', [mock_user()])
    assert process_property_value(notion_data) == ['']


def test_people_person_user():
    notion_person = mock_person_user("Happy Man", 'happyman@gmail.com')
    notion_data = mock_property_value('people', [notion_person])
    assert process_property_value(notion_data) == ['Happy Man']


# TODO: add tests for bot users


def test_checkbox():
    notion_data = mock_property_value('checkbox', True)
    assert process_property_value(notion_data)


def test_url_empty():
    notion_data = mock_property_value('url', None)
    assert process_property_value(notion_data) is None


def test_url_non_empty():
    notion_data = mock_property_value('url', "https://innolitics.com")
    assert process_property_value(notion_data) == "https://innolitics.com"


def test_phone_number_empty():
    notion_data = mock_property_value('phone_number', None)
    assert process_property_value(notion_data) is None


def test_phone_number_non_empty():
    notion_data = mock_property_value('phone_number', "1-555-555-5555")
    assert process_property_value(notion_data) == "1-555-555-5555"


def test_email_empty():
    notion_data = mock_property_value('email', None)
    assert process_property_value(notion_data) is None


def test_email_non_empty():
    notion_data = mock_property_value('email', "info@innolitics.com")
    assert process_property_value(notion_data) == "info@innolitics.com"


def test_formula_number_empty():
    notion_data = mock_formula_property_value('number', None)
    assert process_property_value(notion_data) is None


def test_formula_number_non_empty():
    notion_data = mock_formula_property_value('number', 3)
    assert process_property_value(notion_data) == 3


def test_formula_date_empty():
    notion_data = mock_formula_property_value('date', None)
    assert process_property_value(notion_data) is None


def test_formula_date_start_only():
    notion_data = mock_formula_property_value('date', {'start': '2022-05-11'})
    assert process_property_value(notion_data) == '2022-05-11'


def test_relationship_empty():
    notion_data = mock_property_value('relation', [])
    assert process_property_value(notion_data) == []


def test_relationship_single():
    item = mock_relation_value()
    notion_data = mock_property_value('relation', [item])
    assert process_property_value(notion_data) == [item["id"]]


def test_relationship_double():
    item1 = mock_relation_value()
    item2 = mock_relation_value()
    notion_data = mock_property_value('relation', [item1, item2])
    assert process_property_value(notion_data) == [item1["id"], item2["id"]]


def test_rollup_date_empty():
    notion_data = mock_rollup_property_value('date', None)
    assert process_property_value(notion_data) is None


# TODO: Add some more tests for different types of rollups, including arrays of
# different types of values


@pytest.mark.xfail
def test_rollup_date_array():
    notion_data = mock_rollup_property_value('array', [
        {"start": "2022-05-11"},
        {"start": "2022-05-12"},
        {"start": "2022-05-13"},
    ])
    assert process_property_value(notion_data) == ['2022-05-11', '2022-05-12', '2022-05-12']

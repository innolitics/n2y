import pytest

from n2y.export import _page_properties
from n2y.notion_mocks import mock_page, mock_rich_text_property_value
from n2y import notion


@pytest.fixture
def page():
    property = mock_rich_text_property_value("P")
    notion_page = mock_page(title="T", extra_properties={"property": property})
    client = notion.Client('')
    return client._wrap_notion_page(notion_page)


def test_page_properties_basic(page):
    properties = _page_properties(page)
    assert properties == {"title": "T", "property": "P"}


def test_page_properties_id(page):
    properties = _page_properties(page, id_property="id")
    assert "id" in properties


def test_page_properties_url(page):
    properties = _page_properties(page, url_property="url")
    assert "url" in properties


def test_page_properties_mapping(page):
    properties = _page_properties(page, property_map={"property": "p"})
    assert properties == {"title": "T", "p": "P"}

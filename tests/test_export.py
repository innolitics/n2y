from unittest.mock import patch

import pytest

from n2y import notion
from n2y.export import _page_filename, _page_properties
from n2y.notion_mocks import mock_page, mock_rich_text_property_value, mock_user
from n2y.user import User

pdf = "T.pdf"


@pytest.fixture
@patch("n2y.notion.Client.wrap_notion_user")
def page(wrap_notion_user):
    property_value = mock_rich_text_property_value("P")
    notion_page = mock_page(title="T", extra_properties={"property": property_value})
    client = notion.Client("")
    wrap_notion_user.return_value = User(client, mock_user())
    return client._wrap_notion_page(notion_page)


def test_page_properties_basic(page):
    properties = _page_properties(page)
    assert properties == {"title": "T", "property": "P\n"}


def test_page_properties_id(page):
    properties = _page_properties(page, id_property="id")
    assert "id" in properties


def test_page_properties_url(page):
    properties = _page_properties(page, url_property="url")
    assert "url" in properties


def test_page_properties_mapping(page):
    properties = _page_properties(page, property_map={"property": "p"})
    assert properties == {"title": "T", "p": "P\n"}
    properties = _page_properties(page, property_map={"property": None})
    assert properties == {"title": "T"}


def test_page_filename_no_template(page):
    assert _page_filename(page, "pdf") == pdf
    assert _page_filename(page, "pdf+extra") == pdf
    assert _page_filename(page, "pdf-extra") == pdf
    assert _page_filename(page, "pdf-extra+other") == pdf


def test_page_filename_template(page):
    assert _page_filename(page, "pdf", "{property}.p") == "P.p"
    assert _page_filename(page, "pdf", "{TITLE}.p") == "T.p"
    assert _page_filename(page, "pdf", "{TITLE}-{property}.p") == "T-P.p"


def test_page_filename_template_malformed(page):
    assert _page_filename(page, "pdf", "{missing}.p") == pdf

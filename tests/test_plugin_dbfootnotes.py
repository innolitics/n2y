import pytest

from n2y.blocks import ParagraphBlock
from n2y.database import Database
from n2y.errors import PluginError
from n2y.mentions import PageMention
from n2y.notion import Client
from n2y.notion_mocks import (
    mock_database,
    mock_page,
    mock_page_mention,
    mock_paragraph_block,
)
from n2y.page import Page
from n2y.plugins.dbfootnotes import PageMentionFootnote


def mock_page_mention_with_footnote(
    mentioned_page_parent, connect_parent_correctly=True
):
    client = Client("", plugins=["n2y.plugins.dbfootnotes"])
    # The original page, with the footnote ref.
    original_page = mock_page()
    # A paragraph in the original page where the mention occurs.
    paragraph_with_footnote_ref = mock_paragraph_block("Text with footnote ref")
    # The mention itself.
    mentioned_page = mock_page()
    mention = mock_page_mention()
    mention_text = "1"
    # Connect all of these mocked pages per the expected scenario.
    mention["page"]["id"] = mentioned_page["id"]
    # The parent of the mentioned page should be the inline DB.
    mentioned_page["parent"] = {
        "type": "page_id",
        "page_id": mentioned_page_parent["id"],
    }
    # The parent of the block with the mention should be the original page.
    paragraph_with_footnote_ref["parent"] = {
        "type": "page_id",
        "page_id": original_page["id"],
    }
    # In the correct scenario, the parent of the mentioned page's parent should
    # be the original page (the case of an inline DB).
    if connect_parent_correctly:
        mentioned_page_parent["parent"] = {
            "type": "page_id",
            "page_id": original_page["id"],
        }
        mentioned_page_parent_parent_n2y = Page(client, original_page)
    else:
        not_original_page = mock_page()
        mentioned_page_parent["parent"] = {
            "type": "page_id",
            "page_id": not_original_page["id"],
        }
        mentioned_page_parent_parent_n2y = Page(client, not_original_page)

    # Create `n2y` types from raw data constructed thus far.
    original_page_n2y = Page(client, original_page)
    mentioned_page_n2y = Page(client, mentioned_page)
    if mentioned_page_parent["object"] == "database":
        mentioned_page_parent_n2y = Database(client, mentioned_page_parent)
    else:
        mentioned_page_parent_n2y = Page(client, mentioned_page_parent)
    block = ParagraphBlock(client, paragraph_with_footnote_ref, original_page_n2y)

    page_mention_footnote_n2y = PageMentionFootnote.__new__(PageMentionFootnote)
    PageMention.__init__(page_mention_footnote_n2y, client, mention, mention_text)
    page_mention_footnote_n2y.mentioned_page = mentioned_page_n2y
    page_mention_footnote_n2y.block = block
    page_mention_footnote_n2y.mentioned_page_parent = mentioned_page_parent_n2y
    page_mention_footnote_n2y.mentioned_page_parent_parent = (
        mentioned_page_parent_parent_n2y
    )

    return page_mention_footnote_n2y


def test_check_that_mention_parent_is_a_database():
    from_page_mention_with_page_parent = mock_page_mention_with_footnote(mock_page())
    from_page_mention_with_db_parent = mock_page_mention_with_footnote(
        mock_database("Footnotes")
    )

    assert from_page_mention_with_page_parent._is_footnote() is False
    assert from_page_mention_with_db_parent._is_footnote() is True


def test_check_that_mention_parent_is_inline_db_of_original_page():
    from_page_mention_with_inline_db = mock_page_mention_with_footnote(
        mentioned_page_parent=mock_database("Footnotes"),
        connect_parent_correctly=True,
    )

    assert from_page_mention_with_inline_db._is_footnote() is True

    with pytest.raises(PluginError):
        mock_page_mention_with_footnote(
            mentioned_page_parent=mock_database("Footnotes"),
            connect_parent_correctly=False,
        )._is_footnote()


def test_footnote_db_naming_convention():
    page_mention_prefix = mock_page_mention_with_footnote(
        mock_database("Prefix Footnotes")
    )
    page_mention_suffix = mock_page_mention_with_footnote(
        mock_database("Footnotes Suffix")
    )
    page_mention_case_issue = mock_page_mention_with_footnote(
        mock_database("My footnotes")
    )
    page_mention_plural_issue = mock_page_mention_with_footnote(
        mock_database("My Footnote")
    )

    assert page_mention_prefix._is_footnote() is True
    assert page_mention_suffix._is_footnote() is False
    assert page_mention_case_issue._is_footnote() is False
    assert page_mention_plural_issue._is_footnote() is False

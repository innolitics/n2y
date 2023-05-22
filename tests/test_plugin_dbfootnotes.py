from n2y.database import Database
from n2y.mentions import PageMention
from n2y.notion import Client
from n2y.notion_mocks import mock_database, mock_page, mock_page_mention
from n2y.page import Page
from n2y.plugins.dbfootnotes import PageMentionFootnote


def mock_page_mention_with_footnote(parent):
    client = Client("", plugins=["n2y.plugins.dbfootnotes"])
    mentioned_page = mock_page()
    mentioned_page_parent = parent
    mention = mock_page_mention()
    mention_text = "1"
    mention["page"]["id"] = mentioned_page["id"]
    mentioned_page["parent"] = {
        "type": "page_id",
        "page_id": mentioned_page_parent["id"],
    }

    mentioned_page_n2y = Page(client, mentioned_page)
    if parent["object"] == "database":
        mentioned_page_parent_n2y = Database(client, mentioned_page_parent)
    else:
        mentioned_page_parent_n2y = Page(client, mentioned_page_parent)

    page_mention_footnote_n2y = PageMentionFootnote.__new__(PageMentionFootnote)
    PageMention.__init__(page_mention_footnote_n2y, client, mention, mention_text)
    page_mention_footnote_n2y.mentioned_page = mentioned_page_n2y
    page_mention_footnote_n2y.mentioned_page_parent = mentioned_page_parent_n2y

    return page_mention_footnote_n2y


def test_check_that_mention_parent_is_a_database():
    from_page_mention_with_page_parent = mock_page_mention_with_footnote(mock_page())
    from_page_mention_with_db_parent = mock_page_mention_with_footnote(
        mock_database("Footnotes")
    )

    assert from_page_mention_with_page_parent._is_footnote() is False
    assert from_page_mention_with_db_parent._is_footnote() is True


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

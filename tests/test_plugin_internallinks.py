from unittest.mock import Mock, patch

from n2y.blocks import ChildPageBlock, HeadingOneBlock, ParagraphBlock
from n2y.notion import Client
from n2y.notion_mocks import (
    mock_block,
    mock_heading_block,
    mock_id,
    mock_page,
    mock_rich_text,
    mock_user,
)
from n2y.page import Page
from n2y.plugins.internallinks import (
    find_target_block,
    get_notion_id_from_href,
    is_internal_link,
)
from n2y.user import User
from n2y.utils import header_id_from_text, pandoc_ast_to_markdown


def test_get_notion_id_from_href_simple():
    uid = mock_id()
    assert get_notion_id_from_href(f"/1234#{uid}") == uid


def test_get_notion_id_from_href_missing_fragment():
    assert get_notion_id_from_href("/1234") is None


def test_get_notion_id_from_href_fragment_is_not_uid():
    assert get_notion_id_from_href("/1234#foo") is None


def test_is_internal_link():
    assert is_internal_link("/1234#5678", "1234")


def test_is_not_internal_link():
    assert not is_internal_link("http://silverspoonscollectors.org/foo#bar", "1234")


def test_is_internal_link_missing_href():
    assert not is_internal_link(None, "1234")


@patch("n2y.notion.Client.wrap_notion_user")
def mock_page_with_link_to_header(
    wrap_notion_user, header_text: str = "nice header", link_text: str = "nice link"
) -> Page:
    client = Client("", plugins=["n2y.plugins.internallinks"])
    wrap_notion_user.return_value = User(client, mock_user())

    page = Page(client, notion_data=mock_page())
    page_block = ChildPageBlock(
        client=client,
        notion_data=mock_block("child_page", {"title": "Mock Page"}),
        page=page,
        get_children=False,
    )
    # HACK: should preferably mock Client.get_block, not set private attr
    page._block = page_block

    heading_block = HeadingOneBlock(
        client=client,
        notion_data=mock_heading_block(header_text, level=1),
        page=page,
        get_children=False,
    )

    paragraph_with_link_block = ParagraphBlock(
        client=client,
        notion_data=mock_block(
            "paragraph",
            {
                "rich_text": [
                    mock_rich_text(text="some random text"),
                    mock_rich_text(
                        text=link_text,
                        href=(
                            f"/{page.notion_id.replace('-', '')}"
                            f"#{heading_block.notion_id.replace('-', '')}"
                        ),
                    ),
                ]
            },
        ),
        page=page,
        get_children=False,
    )

    page.block.children = [heading_block, paragraph_with_link_block]
    return page, heading_block, paragraph_with_link_block


def test_find_target_block():
    page, heading, paragraph = mock_page_with_link_to_header()
    assert find_target_block(page.block, target_id=heading.notion_id) is heading
    assert find_target_block(page.block, target_id=paragraph.notion_id) is paragraph


def test_internal_link_to_pandoc():
    header_text = "A Very Fine Title"
    link_text = "A Very Poor Link Text"
    page, _, _ = mock_page_with_link_to_header(
        header_text=header_text,
        link_text=link_text,
    )
    markdown = pandoc_ast_to_markdown(page.to_pandoc(), Mock())
    assert f"# {header_text}" in markdown
    assert f"[{link_text}](#{header_id_from_text(header_text)})" in markdown

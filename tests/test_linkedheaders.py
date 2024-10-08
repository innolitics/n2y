"""
These tests verify how the n2y block classes convert notion data into Pandoc
abstract syntax tree (AST) objects, and then into markdown.
"""

from pandoc.types import Header, Link, Space, Str

from n2y.notion_mocks import mock_block, mock_rich_text
from n2y.utils import header_id_from_text, strip_hyphens
from tests.test_blocks import process_block

linked_headers = ["n2y.plugins.linkedheaders"]


def mock_header_ast(level, suffix, notion_block):
    rich_text = notion_block[notion_block["type"]]["rich_text"][0]["plain_text"]
    section_id = header_id_from_text(rich_text)
    return Header(
        level,
        (section_id, [], []),
        [
            Link(
                ("", [], []),
                [Str("Heading"), Space(), Str(suffix)],
                (f'#{strip_hyphens(notion_block["id"])}', ""),
            )
        ],
    )


def test_heading_1():
    notion_block = mock_block(
        "heading_1", {"rich_text": [mock_rich_text("Heading One")]}
    )
    pandoc_ast, markdown = process_block(notion_block, linked_headers)
    assert pandoc_ast == mock_header_ast(1, "One", notion_block)
    assert markdown == f'# [Heading One]({notion_block["url"]})\n'


def test_heading_1_bolding_stripped():
    notion_block = mock_block(
        "heading_1", {"rich_text": [mock_rich_text("Heading One", ["bold"])]}
    )
    pandoc_ast, markdown = process_block(notion_block, linked_headers)
    assert pandoc_ast == mock_header_ast(1, "One", notion_block)
    assert markdown == f'# [Heading One]({notion_block["url"]})\n'


def test_heading_2():
    notion_block = mock_block(
        "heading_2", {"rich_text": [mock_rich_text("Heading Two")]}
    )
    pandoc_ast, markdown = process_block(notion_block, linked_headers)
    assert pandoc_ast == mock_header_ast(2, "Two", notion_block)
    assert markdown == f'## [Heading Two]({notion_block["url"]})\n'


def test_heading_3():
    notion_block = mock_block(
        "heading_3", {"rich_text": [mock_rich_text("Heading Three")]}
    )
    pandoc_ast, markdown = process_block(notion_block, linked_headers)
    assert pandoc_ast == mock_header_ast(3, "Three", notion_block)
    assert markdown == f'### [Heading Three]({notion_block["url"]})\n'

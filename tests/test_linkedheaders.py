"""
These tests verify how the n2y block classes convert notion data into Pandoc
abstract syntax tree (AST) objects, and then into markdown.
"""
from pandoc.types import (
    Str, Space, Header, Link
)

from tests.notion_mocks import mock_block, mock_rich_text, process_block


def test_heading_1():
    notion_block = mock_block("heading_1", {"rich_text": [mock_rich_text("Heading One")]})
    pandoc_ast, markdown = process_block(notion_block)
    assert pandoc_ast == Header(1, ("", [], []), [Str("Heading"), Space(), Str("One")])
    assert markdown == "# Heading One\n"


def test_heading_1_bolding_stripped():
    notion_block = mock_block("heading_1", {"rich_text": [mock_rich_text("Heading One", ["bold"])]})
    pandoc_ast, markdown = process_block(notion_block)
    assert pandoc_ast == Header(1, ("", [], []), [Str("Heading"), Space(), Str("One")])
    assert markdown == "# Heading One\n"


def test_heading_2():
    notion_block = mock_block("heading_2", {"rich_text": [mock_rich_text("Heading Two")]})
    pandoc_ast, markdown = process_block(notion_block)
    assert pandoc_ast == Header(2, ("", [], []), [Str("Heading"), Space(), Str("Two")])
    assert markdown == "## Heading Two\n"


def test_heading_3():
    notion_block = mock_block("heading_3", {"rich_text": [mock_rich_text("Heading Three")]})
    pandoc_ast, markdown = process_block(notion_block)
    assert pandoc_ast == Header(3, ("", [], []), [Str("Heading"), Space(), Str("Three")])
    assert markdown == "### Heading Three\n"

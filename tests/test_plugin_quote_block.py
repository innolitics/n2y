import pytest
from unittest import mock
from pandoc.types import (
    BlockQuote,
    Div,
    Space,
    Str,
)

from n2y.notion import Client
from n2y.notion_mocks import (
    mock_block,
    mock_paragraph_block,
    mock_rich_text,
    mock_page,
    mock_user,
)
from n2y.page import Page
from n2y.user import User
from n2y.utils import pandoc_ast_to_markdown


def generate_block(notion_block, plugins=None):
    """Generate a block with optional plugins."""
    with mock.patch.object(Client, "get_notion_block") as mock_get_notion_block, \
            mock.patch.object(Client, "wrap_notion_user") as mock_wrap_user:
        mock_get_notion_block.return_value = notion_block
        client = Client("fake_token")
        if plugins:
            client.load_plugins(plugins)
        # Mock the user wrapping
        mock_wrap_user.return_value = User(client, mock_user())
        # Create a mock page to pass to get_block
        mock_page_data = mock_page()
        page = Page(client, mock_page_data)
        n2y_block = client.get_block(notion_block["id"], page)
    return n2y_block


def process_block(notion_block, plugins=None):
    """Process a block and return pandoc AST and markdown."""
    n2y_block = generate_block(notion_block, plugins=plugins)
    pandoc_ast = n2y_block.to_pandoc()
    markdown = pandoc_ast_to_markdown(pandoc_ast, n2y_block.client.logger)
    return pandoc_ast, markdown


def process_parent_block(notion_block, child_notion_blocks, plugins=None):
    """Process a parent block with children and return pandoc AST and markdown."""
    with mock.patch.object(
        Client, "get_child_notion_blocks"
    ) as mock_get_child_notion_blocks:
        mock_get_child_notion_blocks.return_value = child_notion_blocks
        n2y_block = generate_block(notion_block, plugins=plugins)
    pandoc_ast = n2y_block.to_pandoc()
    markdown = pandoc_ast_to_markdown(pandoc_ast, n2y_block.client.logger)
    return pandoc_ast, markdown


def test_quoteblock_plugin_basic():
    """Test basic quoteblock plugin functionality."""
    notion_block = mock_block(
        "quote",
        {
            "rich_text": [
                mock_rich_text(
                    "This is a custom quote block with special styling."
                )
            ]
        },
    )

    # Test with quoteblock plugin loaded
    plugins = ["n2y.plugins.quoteblock"]
    pandoc_ast, markdown = process_block(notion_block, plugins=plugins)

    # Plugin should return a Div with blockquote styling classes
    assert isinstance(pandoc_ast, Div)

    # Check that the Div has both CSS classes and DOCX styling
    # Div structure: Div((id, classes, key-value pairs), content)
    # CSS classes for web styling
    assert pandoc_ast[0][1] == ["blockquote", "notion-quote"]
    # DOCX style
    assert pandoc_ast[0][2] == [("custom-style", "Block Quote")]
    # Test that content is preserved within the Div
    expected_content = [
        Str("This"),
        Space(),
        Str("is"),
        Space(),
        Str("a"),
        Space(),
        Str("custom"),
        Space(),
        Str("quote"),
        Space(),
        Str("block"),
        Space(),
        Str("with"),
        Space(),
        Str("special"),
        Space(),
        Str("styling."),
    ]
    # Access: Div -> content list -> first Para -> Para content
    assert pandoc_ast[1][0][0] == expected_content


def test_quoteblock_plugin_with_formatted_text():
    """Test quoteblock plugin with rich text formatting."""
    notion_block = mock_block(
        "quote",
        {
            "rich_text": [
                mock_rich_text("Bold text", ["bold"]),
                mock_rich_text(" and "),
                mock_rich_text("italic text", ["italic"]),
                mock_rich_text(" in a quote."),
            ]
        },
    )

    plugins = ["n2y.plugins.quoteblock"]
    pandoc_ast, markdown = process_block(notion_block, plugins=plugins)

    # Plugin should return a Div with blockquote styling classes
    assert isinstance(pandoc_ast, Div)

    # Verify the attributes are applied for both web and DOCX compatibility
    assert pandoc_ast[0][1] == ["blockquote", "notion-quote"]  # CSS classes
    assert pandoc_ast[0][2] == [("custom-style", "Block Quote")]  # DOCX style

    # Check that formatting is preserved
    assert "**Bold text**" in markdown  # Bold formatting
    assert "*italic text*" in markdown  # Italic formatting
    assert "in a quote." in markdown


def test_quoteblock_plugin_with_children():
    """Test quoteblock plugin with child blocks."""
    parent = mock_block(
        "quote",
        {
            "rich_text": [mock_rich_text("Parent quote with children")]
        },
        has_children=True,
    )
    children = [mock_paragraph_block([("Child paragraph content", [])])]

    plugins = ["n2y.plugins.quoteblock"]
    pandoc_ast, markdown = process_parent_block(parent, children, plugins=plugins)

    # Plugin should return a Div with styling classes for web compatibility
    assert isinstance(pandoc_ast, Div)

    # Verify the attributes provide both CSS and DOCX styling
    assert pandoc_ast[0][1] == ["blockquote", "notion-quote"]  # CSS classes
    assert pandoc_ast[0][2] == [("custom-style", "Block Quote")]  # DOCX style

    # Should contain both parent and child content
    assert "Parent quote with children" in markdown
    assert "Child paragraph content" in markdown


def test_quoteblock_plugin_vs_default_behavior():
    """Test that plugin changes default quote behavior from BlockQuote to Div."""
    notion_block = mock_block(
        "quote",
        {
            "rich_text": [
                mock_rich_text("Test quote content.")
            ]
        },
    )

    # Test default behavior (without plugin)
    default_pandoc_ast, default_markdown = process_block(
        notion_block, plugins=None
    )

    # Test plugin behavior
    plugin_pandoc_ast, plugin_markdown = process_block(
        notion_block, plugins=["n2y.plugins.quoteblock"]
    )

    # Default should be BlockQuote
    assert isinstance(default_pandoc_ast, BlockQuote)

    # Plugin should return Div with blockquote styling classes
    assert isinstance(plugin_pandoc_ast, Div)
    # CSS classes
    assert plugin_pandoc_ast[0][1] == ["blockquote", "notion-quote"]
    # DOCX style
    assert plugin_pandoc_ast[0][2] == [("custom-style", "Block Quote")]

    # Both should preserve the same content
    assert "Test quote content." in default_markdown
    assert "Test quote content." in plugin_markdown


def test_quoteblock_plugin_color_extraction():
    """Test that plugin extracts color information from Notion data."""
    # Create a mock with color information
    notion_block = mock_block(
        "quote",
        {
            "rich_text": [mock_rich_text("Colored quote content.")],
            "color": "blue"
        },
    )

    plugins = ["n2y.plugins.quoteblock"]
    n2y_block = generate_block(notion_block, plugins=plugins)

    # Check that the plugin block has color extraction capability
    assert hasattr(n2y_block, '_extract_notion_color')
    assert hasattr(n2y_block, 'notion_color')

    # Verify it returns a Div with blockquote styling
    pandoc_ast = n2y_block.to_pandoc()
    assert isinstance(pandoc_ast, Div)
    # CSS classes
    assert pandoc_ast[0][1] == ["blockquote", "notion-quote"]
    # DOCX style
    assert pandoc_ast[0][2] == [("custom-style", "Block Quote")]


if __name__ == "__main__":
    pytest.main([__file__])

from pandoc.types import BulletList, Para, Str, Space, Header

from n2y.notion_mocks import mock_block, mock_rich_text, mock_paragraph_block
from tests.utils import block_colors
from tests.test_blocks import process_parent_block


def process_test_toggle_block(color):
    parent = mock_block(
        "toggle",
        {"rich_text": [mock_rich_text("Toggle text")], "color": color},
        has_children=True,
    )
    children = [
        mock_block("heading_1", {"rich_text": [mock_rich_text("Heading text")]}),
        mock_paragraph_block([("Paragraph text", [])]),
    ]
    return process_parent_block(parent, children, ["n2y.plugins.expandbluetoggles"])


def test_only_children_of_blue_toggles_are_rendered():
    pandoc_ast, markdown = process_test_toggle_block("blue_background")
    assert pandoc_ast == [
        Header(1, ("heading-text", [], []), [Str("Heading"), Space(), Str("text")]),
        Para([Str("Paragraph"), Space(), Str("text")]),
    ]
    assert (
        markdown == """# Heading text

Paragraph text
"""
    )


def test_non_blue_toggles_are_rendered_regularly_with_bullet_list():
    non_blue_colors = block_colors.copy()
    non_blue_colors.remove("blue")
    for color in non_blue_colors:
        pandoc_ast, markdown = process_test_toggle_block(color)
        pandoc_1 = BulletList([
            [
                Para(
                    [Str('Toggle'), Space(), Str('text')]
                ),
                Header(
                    1,
                    ('heading-text', [], []),
                    [Str('Heading'), Space(), Str('text')]
                ),
                Para(
                    [Str('Paragraph'), Space(), Str('text')]
                )
            ]
        ])
        pandoc_2 = [
            Header(
                1,
                ('heading-text', [], []),
                [Str('Heading'), Space(), Str('text')]
            ),
            Para(
                [Str('Paragraph'), Space(), Str('text')]
            )
        ]
        markdown_1 = "# Heading text\n\nParagraph text\n"
        markdown_2 = "-   Toggle text\n\n    # Heading text\n\n    Paragraph text\n"
        assert pandoc_ast == pandoc_1 or pandoc_ast == pandoc_2
        assert markdown == markdown_1 or markdown == markdown_2

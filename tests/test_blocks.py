"""
These tests verify how the n2y block classes convert notion data into Pandoc
abstract syntax tree (AST) objects, and then into markdown.
"""

import re
from unittest import mock

import pytest
from pandoc.types import (
    AlignDefault,
    BlockQuote,
    BulletList,
    Caption,
    Cell,
    CodeBlock,
    ColSpan,
    ColWidthDefault,
    Decimal,
    DisplayMath,
    Header,
    HorizontalRule,
    Image,
    LineBreak,
    Link,
    Math,
    Meta,
    OrderedList,
    Pandoc,
    Para,
    Period,
    Plain,
    Row,
    RowHeadColumns,
    RowSpan,
    Space,
    Str,
    Table,
    TableBody,
    TableFoot,
    TableHead,
)

from n2y.notion import Client
from n2y.notion_mocks import (
    mock_block,
    mock_file,
    mock_id,
    mock_page,
    mock_page_mention,
    mock_paragraph_block,
    mock_rich_text,
    mock_rich_text_array,
    mock_user,
)
from n2y.page import Page
from n2y.user import User
from n2y.utils import pandoc_ast_to_markdown

innolitics_website = "https://innolitics.com"
example_img = "https://example.com/image.png"
toc_headers = [
    Header(
        1,
        ("foo-items-header", [], []),
        [Str("Foo"), Space(), Str("Items"), Space(), Str("Header")],
    ),
    Header(2, ("foo-bar", [], []), [Str("Foo:"), Space(), Str("Bar")]),
    Header(2, ("foo-ski", [], []), [Str("Foo:"), Space(), Str("Ski")]),
    Header(
        3,
        ("first-foo-ski", [], []),
        [Str("First"), Space(), Str("Foo"), Space(), Str("Ski")],
    ),
]
toc_headers_starting_h2 = [
    Header(
        2,
        ("foo-header-h2", [], []),
        [Str("Foo"), Space(), Str("Header"), Space(), Str("H2")],
    ),
    Header(
        3,
        ("foo-bar-h3", [], []),
        [Str("Foo:"), Space(), Str("Bar"), Space(), Str("H3")],
    ),
    Header(
        3,
        ("foo-ski-h3", [], []),
        [Str("Foo:"), Space(), Str("Ski"), Space(), Str("H3")],
    ),
    Header(
        4,
        ("first-foo-ski", [], []),
        [Str("First"), Space(), Str("Foo"), Space(), Str("Ski")],
    ),
]
toc_item_ast = [
    Plain(
        [
            Link(
                ("", [], []),
                [Str("Foo"), Space(), Str("Items"), Space(), Str("Header")],
                ("#foo-items-header", ""),
            )
        ]
    ),
    OrderedList(
        (1, Decimal(), Period()),
        [
            [
                Plain(
                    [
                        Link(
                            ("", [], []),
                            [Str("Foo:"), Space(), Str("Bar")],
                            ("#foo-bar", ""),
                        )
                    ]
                )
            ],
            [
                Plain(
                    [
                        Link(
                            ("", [], []),
                            [Str("Foo:"), Space(), Str("Ski")],
                            ("#foo-ski", ""),
                        )
                    ]
                ),
                OrderedList(
                    (1, Decimal(), Period()),
                    [
                        [
                            Plain(
                                [
                                    Link(
                                        ("", [], []),
                                        [
                                            Str("First"),
                                            Space(),
                                            Str("Foo"),
                                            Space(),
                                            Str("Ski"),
                                        ],
                                        ("#first-foo-ski", ""),
                                    )
                                ]
                            )
                        ]
                    ],
                ),
            ],
        ],
    ),
]


def generate_block(notion_block, plugins=None):
    with mock.patch.object(Client, "get_notion_block") as mock_get_notion_block:
        mock_get_notion_block.return_value = notion_block
        client = Client("", plugins=plugins)
        page = None
        return client.get_block("unusedid", page)


def process_block(notion_block, plugins=None):
    n2y_block = generate_block(notion_block, plugins=plugins)
    pandoc_ast = n2y_block.to_pandoc()
    markdown = pandoc_ast_to_markdown(pandoc_ast, n2y_block.client.logger)
    return pandoc_ast, markdown


def process_parent_block(notion_block, child_notion_blocks, plugins=None):
    with mock.patch.object(
        Client, "get_child_notion_blocks"
    ) as mock_get_child_notion_blocks:
        mock_get_child_notion_blocks.return_value = child_notion_blocks
        n2y_block = generate_block(notion_block, plugins)
    pandoc_ast = n2y_block.to_pandoc()
    markdown = pandoc_ast_to_markdown(pandoc_ast, n2y_block.client.logger)
    return pandoc_ast, markdown


def test_unknown_block_type():
    notion_block = mock_block("abcdef", {})
    with pytest.raises(NotImplementedError) as e:
        process_block(notion_block)
    assert "abcdef" in str(e)


def test_paragraph():
    notion_block = mock_paragraph_block([("paragraph text", [])])
    pandoc_ast, markdown = process_block(notion_block)
    assert pandoc_ast == Para([Str("paragraph"), Space(), Str("text")])
    assert markdown == "paragraph text\n"


def test_paragraph_children_have_block_references():
    notion_block = mock_block(
        "paragraph",
        {
            "color": "default",
            "rich_text": [mock_rich_text("m", mention=mock_page_mention())],
        },
    )
    n2y_block = generate_block(notion_block)
    assert n2y_block.rich_text.block == n2y_block
    assert n2y_block.rich_text[0].block == n2y_block
    assert n2y_block.rich_text[0].mention.block == n2y_block


def test_paragraph_with_child_paragraph():
    parent = mock_block("paragraph", {"rich_text": [mock_rich_text("parent")]}, True)
    children = [mock_paragraph_block([("child", [])])]
    pandoc_ast, markdown = process_parent_block(parent, children)
    assert pandoc_ast == [Para([Str("parent")]), Para([Str("child")])]
    assert markdown == "parent\n\nchild\n"


def test_heading_1():
    notion_block = mock_block("heading_1", {"rich_text": [mock_rich_text("Heading One")]})
    pandoc_ast, markdown = process_block(notion_block)
    assert pandoc_ast == Header(
        1, ("heading-one", [], []), [Str("Heading"), Space(), Str("One")]
    )
    assert markdown == "# Heading One\n"


def test_heading_1_bolding_stripped():
    notion_block = mock_block(
        "heading_1", {"rich_text": [mock_rich_text("Heading One", ["bold"])]}
    )
    pandoc_ast, markdown = process_block(notion_block)
    assert pandoc_ast == Header(
        1, ("heading-one", [], []), [Str("Heading"), Space(), Str("One")]
    )
    assert markdown == "# Heading One\n"


def test_heading_2():
    notion_block = mock_block("heading_2", {"rich_text": [mock_rich_text("Heading Two")]})
    pandoc_ast, markdown = process_block(notion_block)
    assert pandoc_ast == Header(
        2, ("heading-two", [], []), [Str("Heading"), Space(), Str("Two")]
    )
    assert markdown == "## Heading Two\n"


def test_heading_3():
    notion_block = mock_block(
        "heading_3", {"rich_text": [mock_rich_text("Heading Three")]}
    )
    pandoc_ast, markdown = process_block(notion_block)
    assert pandoc_ast == Header(
        3, ("heading-three", [], []), [Str("Heading"), Space(), Str("Three")]
    )
    assert markdown == "### Heading Three\n"


def test_bulleted_list():
    parent = mock_paragraph_block([("Bulleted List", [])], has_children=True)
    children = [
        mock_block("bulleted_list_item", {"rich_text": [mock_rich_text("Item One")]}),
        mock_block("bulleted_list_item", {"rich_text": [mock_rich_text("Item Two")]}),
    ]
    pandoc_ast, markdown = process_parent_block(parent, children)
    assert pandoc_ast == [
        Para([Str("Bulleted"), Space(), Str("List")]),
        BulletList(
            [
                [Plain([Str("Item"), Space(), Str("One")])],
                [Plain([Str("Item"), Space(), Str("Two")])],
            ]
        ),
    ]
    assert markdown == "Bulleted List\n\n-   Item One\n-   Item Two\n"


def test_numbered_list():
    parent = mock_paragraph_block([("Numbered List", [])], has_children=True)
    children = [
        mock_block("numbered_list_item", {"rich_text": [mock_rich_text("Item One")]}),
        mock_block("numbered_list_item", {"rich_text": [mock_rich_text("Item Two")]}),
    ]
    pandoc_ast, markdown = process_parent_block(parent, children)
    assert pandoc_ast == [
        Para([Str("Numbered"), Space(), Str("List")]),
        OrderedList(
            (1, Decimal(), Period()),
            [
                [Plain([Str("Item"), Space(), Str("One")])],
                [Plain([Str("Item"), Space(), Str("Two")])],
            ],
        ),
    ]
    assert markdown == "Numbered List\n\n1.  Item One\n2.  Item Two\n"


def test_page():
    parent = mock_block("child_page", {"title": "Simple Page"}, has_children=True)
    children = [mock_paragraph_block([("Simple page", [])])]
    pandoc_ast, markdown = process_parent_block(parent, children)
    assert pandoc_ast == Pandoc(
        Meta({}),
        [Para([Str("Simple"), Space(), Str("page")])],
    )
    assert markdown == "Simple page\n"


def test_bookmark_with_caption():
    notion_block = mock_block(
        "bookmark",
        {
            "caption": [mock_rich_text("Innolitics")],
            "url": innolitics_website,
        },
    )
    pandoc_ast, markdown = process_block(notion_block)
    assert pandoc_ast == Para(
        [Link(("", [], []), [Str("Innolitics")], (innolitics_website, ""))]
    )
    assert markdown == "[Innolitics](https://innolitics.com)\n"


def test_bookmark_without_caption():
    notion_block = mock_block(
        "bookmark",
        {
            "caption": [],
            "url": innolitics_website,
        },
    )
    pandoc_ast, markdown = process_block(notion_block)
    assert pandoc_ast == Para(
        [
            Link(
                ("", [], []),
                [Str(innolitics_website)],
                (innolitics_website, ""),
            )
        ]
    )
    assert markdown == "<https://innolitics.com>\n"


def test_divider():
    notion_block = mock_block("divider", {"divider": []})
    pandoc_ast, markdown = process_block(notion_block)
    assert pandoc_ast == HorizontalRule()
    assert re.match("-+", markdown)


def test_block_quote():
    notion_block = mock_block(
        "quote",
        {
            "rich_text": [
                mock_rich_text(
                    "In a time of deceit telling the truth is a revolutionary act."
                ),
            ]
        },
    )
    pandoc_ast, markdown = process_block(notion_block)
    assert pandoc_ast == BlockQuote(
        [
            Para(
                [
                    Str("In"),
                    Space(),
                    Str("a"),
                    Space(),
                    Str("time"),
                    Space(),
                    Str("of"),
                    Space(),
                    Str("deceit"),
                    Space(),
                    Str("telling"),
                    Space(),
                    Str("the"),
                    Space(),
                    Str("truth"),
                    Space(),
                    Str("is"),
                    Space(),
                    Str("a"),
                    Space(),
                    Str("revolutionary"),
                    Space(),
                    Str("act."),
                ]
            )
        ]
    )
    expected_markdown = (
        "> In a time of deceit telling the truth is a revolutionary act.\n"
    )
    assert markdown == expected_markdown


@mock.patch.object(Client, "download_file")
def test_image_internal_with_caption(mock_download):
    notion_block = mock_block(
        "image",
        {
            "type": "file",
            "caption": [mock_rich_text("test image")],
            "file": mock_file(example_img),
        },
    )
    mock_download.return_value = "image.png"
    pandoc_ast, markdown = process_block(notion_block)
    assert pandoc_ast == Para(
        [
            Image(
                ("", [], []),
                [Str("test"), Space(), Str("image")],
                ("image.png", "fig:"),
            )
        ]
    )
    assert markdown == "![test image](image.png)\n"


def test_image_external_without_caption():
    notion_block = mock_block(
        "image",
        {
            "type": "external",
            "caption": [],
            "external": {"url": example_img},
        },
    )
    pandoc_ast, markdown = process_block(notion_block)
    assert pandoc_ast == Para(
        [
            Image(
                ("", [], []),
                [],
                (example_img, ""),
            )
        ]
    )
    assert markdown == "![](https://example.com/image.png)\n"


def test_equation_block():
    lhs = "{\\displaystyle i\\hbar {\\frac {d}{dt}}\\vert "
    rhs = "\\Psi (t)\\rangle={\\hat {H}}\\vert \\Psi (t)\\rangle}"
    example_equation = f"{lhs}{rhs}"
    notion_block = mock_block("equation", {"expression": example_equation})
    pandoc_ast, markdown = process_block(notion_block)
    assert pandoc_ast == Para([Math(DisplayMath(), example_equation)])
    expected_lhs = "$${\\displaystyle i\\hbar {\\frac {d}{dt}}\\vert "
    expected_rhs = "\\Psi (t)\\rangle={\\hat {H}}\\vert \\Psi (t)\\rangle}$$\n"
    expected_markdown = f"{expected_lhs}{expected_rhs}"
    assert markdown == expected_markdown


def test_code_block():
    notion_block = mock_block(
        "code",
        {
            "rich_text": [mock_rich_text("const a = 3")],
            "caption": [],
            "language": "javascript",
        },
    )
    pandoc_ast, markdown = process_block(notion_block)
    assert pandoc_ast == CodeBlock(("", ["javascript"], []), "const a = 3")
    assert markdown == "``` javascript\nconst a = 3\n```\n"


def test_table_block():
    parent = mock_block(
        "table",
        {
            "table_width": 2,
            "has_column_header": True,
            "has_row_header": False,
        },
        has_children=True,
    )
    children = [
        mock_block(
            "table_row",
            {
                "cells": [
                    [mock_rich_text("header1")],
                    [mock_rich_text("header2")],
                ]
            },
        ),
        mock_block(
            "table_row",
            {
                "cells": [
                    [mock_rich_text("one")],
                    [mock_rich_text("two")],
                ]
            },
        ),
        mock_block(
            "table_row",
            {
                "cells": [
                    [mock_rich_text("three\n3.5")],
                    [mock_rich_text("four")],
                ]
            },
        ),
    ]
    pandoc_ast, markdown = process_parent_block(parent, children)
    assert pandoc_ast == Table(
        ("", [], []),
        Caption(None, []),
        [(AlignDefault(), ColWidthDefault()), (AlignDefault(), ColWidthDefault())],
        TableHead(
            ("", [], []),
            [
                Row(
                    ("", [], []),
                    [
                        Cell(
                            ("", [], []),
                            AlignDefault(),
                            RowSpan(1),
                            ColSpan(1),
                            [Plain([Str("header1")])],
                        ),
                        Cell(
                            ("", [], []),
                            AlignDefault(),
                            RowSpan(1),
                            ColSpan(1),
                            [Plain([Str("header2")])],
                        ),
                    ],
                )
            ],
        ),
        [
            TableBody(
                ("", [], []),
                RowHeadColumns(0),
                [],
                [
                    Row(
                        ("", [], []),
                        [
                            Cell(
                                ("", [], []),
                                AlignDefault(),
                                RowSpan(1),
                                ColSpan(1),
                                [Plain([Str("one")])],
                            ),
                            Cell(
                                ("", [], []),
                                AlignDefault(),
                                RowSpan(1),
                                ColSpan(1),
                                [Plain([Str("two")])],
                            ),
                        ],
                    ),
                    Row(
                        ("", [], []),
                        [
                            Cell(
                                ("", [], []),
                                AlignDefault(),
                                RowSpan(1),
                                ColSpan(1),
                                [Plain([Str("three"), LineBreak(), Str("3.5")])],
                            ),
                            Cell(
                                ("", [], []),
                                AlignDefault(),
                                RowSpan(1),
                                ColSpan(1),
                                [Plain([Str("four")])],
                            ),
                        ],
                    ),
                ],
            )
        ],
        TableFoot(("", [], []), []),
    )
    assert (
        markdown
        == "  -------------------\n"
        "  header1   header2\n"
        "  --------- ---------\n"
        "  one       two\n"
        "\n  three\\    four\n"
        "  3.5       \n  "
        "-------------------\n"
    )


def test_toggle():
    parent = mock_block(
        "toggle",
        {
            "rich_text": [
                mock_rich_text("Toggle Header"),
            ]
        },
        has_children=True,
    )
    children = [mock_paragraph_block([("Toggle Content", [])])]
    pandoc_ast, markdown = process_parent_block(parent, children)
    assert pandoc_ast == BulletList(
        [
            [
                Para([Str("Toggle"), Space(), Str("Header")]),
                Para([Str("Toggle"), Space(), Str("Content")]),
            ]
        ]
    )
    assert markdown == "-   Toggle Header\n\n    Toggle Content\n"


def test_todo_in_paragraph():
    parent = mock_block(
        "paragraph",
        {
            "rich_text": [
                mock_rich_text("Task List"),
            ]
        },
        has_children=True,
    )
    children = [
        mock_block("to_do", {"rich_text": [mock_rich_text("Task One")], "checked": True}),
        mock_block(
            "to_do", {"rich_text": [mock_rich_text("Task Two")], "checked": False}
        ),
    ]
    pandoc_ast, markdown = process_parent_block(parent, children)
    assert pandoc_ast == [
        Para([Str("Task"), Space(), Str("List")]),
        BulletList(
            [
                [Plain([Str("☒"), Space(), Str("Task"), Space(), Str("One")])],
                [Plain([Str("☐"), Space(), Str("Task"), Space(), Str("Two")])],
            ]
        ),
    ]
    assert markdown == "Task List\n\n-   [x] Task One\n-   [ ] Task Two\n"


@pytest.mark.xfail(reason="Its unclear how to represent empty todos in pandoc")
def test_todo_empty():
    notion_block = mock_block("to_do", {"rich_text": [], "checked": False})
    _, markdown = process_block(notion_block)
    assert markdown == "-   [ ] \n"


def test_callout():
    parent = mock_block(
        "callout", {"rich_text": [mock_rich_text("Callout")]}, has_children=True
    )
    children = [mock_paragraph_block([("Children", [])])]
    pandoc_ast, markdown = process_parent_block(parent, children)
    assert pandoc_ast == [Para([Str("Callout")]), Para([Str("Children")])]
    assert markdown == "Callout\n\nChildren\n"


def test_synced_block_shared():
    original_synced_block = mock_block(
        "synced_block", {"synced_from": None}, has_children=True
    )
    reference_synced_block = mock_block(
        "synced_block",
        {"synced_from": {"type": "block_id", "block_id": "some-block-id"}},
        has_children=True,
    )
    children = [mock_paragraph_block([("synced", [])])]
    original_pandoc_ast, original_markdown = process_parent_block(
        original_synced_block,
        children,
    )
    reference_pandoc_ast, reference_markdown = process_parent_block(
        reference_synced_block,
        children,
    )
    assert original_pandoc_ast == reference_pandoc_ast == [Para([Str("synced")])]
    assert original_markdown == reference_markdown == "synced\n"


def test_synced_block_unshared():
    unshared_reference_synced_block = mock_block(
        "synced_block",
        {"synced_from": {"type": "block_id", "block_id": "some-block-id"}},
        has_children=False,
    )
    unshared_reference_pandoc_ast, unshared_reference_markdown = process_parent_block(
        unshared_reference_synced_block,
        None,
    )
    assert unshared_reference_pandoc_ast is None
    assert unshared_reference_markdown == ""


def test_link_to_page_page():
    mock_link_to_page_block = mock_block(
        "link_to_page",
        {"type": "page_id", "page_id": mock_id()},
    )
    page = mock_page("Linked Page")
    with mock.patch("n2y.notion.Client._get_url", return_value=page):
        pandoc_ast, markdown = process_block(mock_link_to_page_block)
    assert pandoc_ast == Para([Str("Linked"), Space(), Str("Page")])
    assert markdown == "Linked Page\n"


def test_column_block():
    column_block = mock_block("column", {}, has_children=True)
    children = [mock_paragraph_block([("child", [])])]
    with mock.patch.object(
        Client, "get_child_notion_blocks"
    ) as mock_get_child_notion_blocks:
        mock_get_child_notion_blocks.return_value = children
        n2y_block = generate_block(column_block)
    pandoc_ast = n2y_block.to_pandoc()
    assert pandoc_ast == [Para([Str("child")])]


@mock.patch("n2y.notion.Client.get_child_notion_blocks")
def test_column_list_block(mock_get_child_notion_blocks):
    column_list_block = mock_block("column_list", {}, True)
    column1, column2 = mock_block("column", {}, True), mock_block("column", {}, True)
    para1, para2 = mock_paragraph_block([["child1"]]), mock_paragraph_block([["child2"]])
    # Return [column1, column2] for the column list get_child_notion_blocks call
    # and [para1] and [para2] for the get_child_notion_blocks calls of the
    # respective column blocks
    mock_get_child_notion_blocks.side_effect = [[column1, column2], [para1], [para2]]
    pandoc_ast, markdown = process_block(column_list_block)
    assert pandoc_ast == [Para([Str("child1")]), Para([Str("child2")])]
    assert markdown == "child1\n\nchild2\n"


def test_toc_item_block():
    contents = {
        "header": toc_headers[0],
        "subheaders": toc_headers[1:],
        "rich_text": mock_rich_text_array(
            [("Foo Items Header", None, "#foo-items-header")]
        ),
    }
    toc_item_block = mock_block("table_of_contents_item", contents)
    pandoc_ast, markdown = process_block(toc_item_block)
    assert pandoc_ast == toc_item_ast
    assert (
        markdown
        == """\
[Foo Items Header](#foo-items-header)

1.  [Foo: Bar](#foo-bar)
2.  [Foo: Ski](#foo-ski)
    1.  [First Foo Ski](#first-foo-ski)
"""
    )


def test_toc_block():
    toc_block = mock_block("table_of_contents", {})
    client = Client("")
    toc = client.wrap_notion_block(toc_block, None, True)
    toc.render_toc([*toc_headers, *toc_headers])
    pandoc_ast = toc.to_pandoc()
    markdown = pandoc_ast_to_markdown(pandoc_ast, client.logger)
    assert pandoc_ast == [
        OrderedList((1, Decimal(), Period()), [toc_item_ast, toc_item_ast])
    ]
    assert (
        markdown
        == """\
1.  [Foo Items Header](#foo-items-header)
    1.  [Foo: Bar](#foo-bar)
    2.  [Foo: Ski](#foo-ski)
        1.  [First Foo Ski](#first-foo-ski)
2.  [Foo Items Header](#foo-items-header)
    1.  [Foo: Bar](#foo-bar)
    2.  [Foo: Ski](#foo-ski)
        1.  [First Foo Ski](#first-foo-ski)
"""
    )


def test_toc_block_starting_h2():
    toc_block = mock_block("table_of_contents", {})
    client = Client("")
    toc = client.wrap_notion_block(toc_block, None, True)
    toc.render_toc([*toc_headers_starting_h2, *toc_headers_starting_h2])
    pandoc_ast = toc.to_pandoc()
    markdown = pandoc_ast_to_markdown(pandoc_ast, client.logger)
    assert (
        markdown
        == """\
1.  [Foo Header H2](#foo-header-h2)
    1.  [Foo: Bar H3](#foo-bar-h3)
    2.  [Foo: Ski H3](#foo-ski-h3)
        1.  [First Foo Ski](#first-foo-ski)
2.  [Foo Header H2](#foo-header-h2)
    1.  [Foo: Bar H3](#foo-bar-h3)
    2.  [Foo: Ski H3](#foo-ski-h3)
        1.  [First Foo Ski](#first-foo-ski)
"""
    )


@mock.patch("n2y.notion.Client.wrap_notion_user")
def test_toc_block_h1_after_h2_base(wrap_notion_user):
    toc_block = mock_block("table_of_contents", {})
    client = Client("")
    wrap_notion_user.return_value = User(client, mock_user())
    page_data = mock_page("Mock Page")
    page = Page(client, page_data)
    toc = client.wrap_notion_block(toc_block, page, True)
    toc.render_toc([*toc_headers_starting_h2, *toc_headers])
    pandoc_ast = toc.to_pandoc()
    markdown = pandoc_ast_to_markdown(pandoc_ast, client.logger)
    assert (
        markdown
        == """\
1.  [Foo Header H2](#foo-header-h2)
    1.  [Foo: Bar H3](#foo-bar-h3)
    2.  [Foo: Ski H3](#foo-ski-h3)
        1.  [First Foo Ski](#first-foo-ski)
2.  [Foo: Bar](#foo-bar)
3.  [Foo: Ski](#foo-ski)
    1.  [First Foo Ski](#first-foo-ski)
"""
    )

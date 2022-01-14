from lib2to3.pytree import convert
import pytest
from n2y import converter
import pandoc
from pandoc.types import Str, Para, Plain, Space, Header, Strong, Emph, Strikeout,\
    Code, BulletList, OrderedList, Decimal, Period, Meta, Pandoc

import json
from os.path import join, dirname

default_annotation = {"bold": False, "italic": False, "strikethrough": False,
                      "underline": False, "code": False, "color": "default"}


def test_unknown_block_type():
    input = {"type": "not implemented",
             "has_children": False,
             "paragraph": {
                 "text": [
                     {
                         "annotations": default_annotation,
                         "plain_text": "paragraph text"}
                 ]}}

    with pytest.raises(NotImplementedError):
        converter._parse_block(input)


def test_parse_paragraph():
    input = {"type": "paragraph",
             "has_children": False,
             "paragraph": {
                 "text": [
                     {
                         "annotations": default_annotation,
                         "plain_text": "paragraph text"}
                 ]}}

    pandoc_output = converter._parse_block(input)
    assert pandoc_output == [Para([Str("paragraph"), Space(), Str("text")])]

    markdown_output = pandoc.write(pandoc_output)
    assert markdown_output == "paragraph text\r\n"


def test_parse_heading_1():
    input = {"type": "heading_1",
             "has_children": False,
             "heading_1": {
                 "text": [
                     {
                         "annotations": default_annotation,
                         "plain_text": "Heading One"}
                 ]}}

    pandoc_output = converter._parse_block(input)
    assert pandoc_output == [Header(1, ("", [], []), [Str("Heading"), Space(), Str("One")])]

    markdown_output = pandoc.write(pandoc_output)
    assert markdown_output == "# Heading One\r\n"


def test_parse_heading_2():
    input = {"type": "heading_2",
             "has_children": False,
             "heading_2": {
                 "text": [
                     {
                         "annotations": default_annotation,
                         "plain_text": "Heading Two"}
                 ]}}

    pandoc_output = converter._parse_block(input)
    assert pandoc_output == [Header(2, ("", [], []), [Str("Heading"), Space(), Str("Two")])]

    markdown_output = pandoc.write(pandoc_output)
    assert markdown_output == "## Heading Two\r\n"


def test_parse_heading_3():
    input = {"type": "heading_3",
             "has_children": False,
             "heading_3": {
                 "text": [
                     {
                         "annotations": default_annotation,
                         "plain_text": "Heading Three"}
                 ]}}

    pandoc_output = converter._parse_block(input)
    assert pandoc_output == [Header(3, ("", [], []), [Str("Heading"), Space(), Str("Three")])]

    markdown_output = pandoc.write(pandoc_output)
    assert markdown_output == "### Heading Three\r\n"


def test_bulleted_list():
    input = {"type": "paragraph",
             "has_children": True,
             "paragraph": {
                 "has_children": True,
                 "text": [
                     {
                         "annotations": default_annotation,
                         "plain_text": "Bulleted List"}
                 ]},
             "children": [
                 {
                     "type": "bulleted_list_item",
                     "has_children": False,
                     "bulleted_list_item": {
                         "text": [{
                             "annotations": default_annotation,
                             "plain_text": "Item One"
                         }]
                     }
                 },
                 {
                     "type": "bulleted_list_item",
                     "has_children": False,
                     "bulleted_list_item": {
                         "text": [{
                             "annotations": default_annotation,
                             "plain_text": "Item Two"
                         }]
                     }
                 }
             ]
             }
    pandoc_output = converter._parse_block(input)
    assert pandoc_output == [Para([Str("Bulleted"), Space(), Str("List")]),
                             BulletList([[Plain([Str("Item"), Space(), Str("One")])],
                                         [Plain([Str("Item"), Space(), Str("Two")])]])]

    markdown_output = pandoc.write(pandoc_output)
    expected_markdown = "Bulleted List\r\n\r\n-   Item One\r\n-   Item Two\r\n"
    assert markdown_output == expected_markdown


def test_numbered_list():
    input = {"type": "paragraph",
             "has_children": True,
             "paragraph": {
                 "has_children": True,
                 "text": [
                     {
                         "annotations": default_annotation,
                         "plain_text": "Numbered List"}
                 ]},
             "children": [
                 {
                     "type": "numbered_list_item",
                     "has_children": False,
                     "numbered_list_item": {
                         "text": [{
                             "annotations": default_annotation,
                             "plain_text": "Item One"
                         }]
                     }
                 },
                 {
                     "type": "numbered_list_item",
                     "has_children": False,
                     "numbered_list_item": {
                         "text": [{
                             "annotations": default_annotation,
                             "plain_text": "Item Two"
                         }]
                     }
                 }
             ]
             }
    pandoc_output = converter._parse_block(input)
    assert pandoc_output == [Para([Str("Numbered"), Space(), Str("List")]),
                             OrderedList((1, Decimal(), Period()),
                                         [[Plain([Str("Item"), Space(), Str("One")])],
                                          [Plain([Str("Item"), Space(), Str("Two")])]])]

    markdown_output = pandoc.write(pandoc_output)
    expected_markdown = "Numbered List\r\n\r\n1.  Item One\r\n2.  Item Two\r\n"
    assert markdown_output == expected_markdown


def test_numbered_and_bulleted_list():
    input = {"type": "paragraph",
             "has_children": True,
             "paragraph": {
                 "has_children": True,
                 "text": [
                     {
                         "annotations": default_annotation,
                         "plain_text": "Mixed List"}
                 ]},
             "children": [
                 {
                     "type": "numbered_list_item",
                     "has_children": False,
                     "numbered_list_item": {
                         "text": [{
                             "annotations": default_annotation,
                             "plain_text": "Item One"
                         }]
                     }
                 },
                 {
                     "type": "bulleted_list_item",
                     "has_children": False,
                     "bulleted_list_item": {
                         "text": [{
                             "annotations": default_annotation,
                             "plain_text": "Bulleted item"
                         }]
                     }
                 },
                 {
                     "type": "numbered_list_item",
                     "has_children": False,
                     "numbered_list_item": {
                         "text": [{
                             "annotations": default_annotation,
                             "plain_text": "Item Two"
                         }]
                     }
                 },
                 {
                     "type": "bulleted_list_item",
                     "has_children": False,
                     "bulleted_list_item": {
                         "text": [{
                             "annotations": default_annotation,
                             "plain_text": "Bulleted item two"
                         }]
                     }
                 },
             ]
             }
    pandoc_output = converter._parse_block(input)
    assert pandoc_output == [Para([Str("Mixed"), Space(), Str("List")]),
                             OrderedList((1, Decimal(), Period()), [
                                         [Plain([Str("Item"), Space(), Str("One")])]]),
                             BulletList([[Plain([Str("Bulleted"), Space(), Str("item")])]]),
                             OrderedList((1, Decimal(), Period()), [
                                 [Plain([Str("Item"), Space(), Str("Two")])]]),
                             BulletList([[Plain([Str("Bulleted"), Space(),
                                                 Str("item"), Space(), Str("two")])]])]

    markdown_output = pandoc.write(pandoc_output)
    expected_markdown = (
        "Mixed List\r\n"
        "\r\n"
        "1.  Item One\r\n"
        "\r\n"
        "-   Bulleted item\r\n"
        "\r\n"
        "1.  Item Two\r\n"
        "\r\n"
        "-   Bulleted item two\r\n")

    assert markdown_output == expected_markdown


def test_list_complex():
    f = open(join(dirname(__file__), "notion_complex_list.json"))
    input = json.load(f)
    f.close()

    pandoc_output = converter.convert(input)
    assert pandoc_output == Pandoc(Meta({}), [OrderedList((1, Decimal(), Period()), [
        [Plain([Str("item"), Space(), Str("one")]),
         OrderedList((1, Decimal(), Period()), [
             [Plain([Str("sub"), Space(), Str("item"), Space(), Str("one")]),
              BulletList([[Plain([Str("bulleted"), Space(), Str("item"), Space(), Str("one")])], [
                  Plain([Str("bulleted"), Space(), Str("item"), Space(), Str("one")]),
                  Para([Str("skip"), Space(), Str("bullet")])]])],
             [Plain([Str("subitem"), Space(), Str("two")]),
                 Para([Str("skip"), Space(), Str("number")])]])],
        [Plain([Str("item"), Space(), Str("two")])]]),
        Para([Str("Paragraph"), Space(), Str("after"), Space(), Str("a"),
              Space(), Str("numbered"), Space(), Str("list")])])

    markdown_output = pandoc.write(pandoc_output)
    expected_markdown = (
        "1.  item one\r\n"
        "    1.  sub item one\r\n"
        "        -   bulleted item one\r\n"
        "        -   bulleted item one\r\n"
        "            skip bullet\r\n"
        "    2.  subitem two\r\n"
        "        skip number\r\n"
        "2.  item two\r\n"
        "\r\n"
        "Paragraph after a numbered list\r\n")
    assert markdown_output == expected_markdown


def test_convert():
    input = {"type": "page",
             "content": [
                 {
                     "type": "paragraph",
                     "has_children": False,
                     "paragraph": {
                         "text": [
                             {"annotations": default_annotation, "plain_text": "Simple page"},
                         ]
                     }
                 }, ]
             }
    pandoc_output = converter.convert(input)
    assert pandoc_output == Pandoc(Meta({}), [Para([Str("Simple"), Space(), Str("page")])])

    markdown_output = pandoc.write(pandoc_output)
    expected_markdown = "Simple page\r\n"
    assert markdown_output == expected_markdown


def test_bold_word():
    input = {
        "type": "paragraph",
        "has_children": False,
        "paragraph": {
                "text": [
                    {"annotations": default_annotation, "plain_text": "A "},
                    {"annotations": {"bold": True, "italic": False, "strikethrough": False,
                                     "underline": False, "code": False, "color": "default"},
                        "plain_text": "bold"},
                    {"annotations": default_annotation, "plain_text": " word."},
                ]
        }
    }

    pandoc_output = converter._parse_block(input)
    assert pandoc_output == [Para([Str("A"), Space(),
                                   Strong([Str("bold")]), Space(), Str("word.")])]

    markdown_output = pandoc.write(pandoc_output)
    expected_markdown = "A **bold** word.\r\n"
    assert markdown_output == expected_markdown


def test_bold_letter():
    input = {
        "type": "paragraph",
        "has_children": False,
        "paragraph": {
                "text": [
                    {"annotations": default_annotation, "plain_text": "A "},
                    {"annotations": {"bold": True, "italic": False, "strikethrough": False,
                                     "underline": False, "code": False, "color": "default"},
                        "plain_text": "b"},
                    {"annotations": default_annotation, "plain_text": "old word."},
                ]
        }
    }

    pandoc_output = converter._parse_block(input)
    assert pandoc_output == [Para([Str("A"), Space(),
                                   Strong([Str("b")]), Str("old"), Space(), Str("word.")])]

    markdown_output = pandoc.write(pandoc_output)
    expected_markdown = "A **b**old word.\r\n"
    assert markdown_output == expected_markdown


def test_italic_word():
    input = {
        "type": "paragraph",
        "has_children": False,
        "paragraph": {
                "text": [
                    {"annotations": default_annotation, "plain_text": "An "},
                    {"annotations": {"bold": False, "italic": True, "strikethrough": False,
                                     "underline": False, "code": False, "color": "default"},
                        "plain_text": "italic"},
                    {"annotations": default_annotation, "plain_text": " word."},
                ]
        }
    }

    pandoc_output = converter._parse_block(input)
    assert pandoc_output == [Para([Str("An"), Space(),
                                   Emph([Str("italic")]), Space(), Str("word.")])]

    markdown_output = pandoc.write(pandoc_output)
    expected_markdown = "An *italic* word.\r\n"
    assert markdown_output == expected_markdown


def test_italic_letter():
    input = {
        "type": "paragraph",
        "has_children": False,
        "paragraph": {
                "text": [
                    {"annotations": default_annotation, "plain_text": "An "},
                    {"annotations": {"bold": False, "italic": True, "strikethrough": False,
                                     "underline": False, "code": False, "color": "default"},
                        "plain_text": "i"},
                    {"annotations": default_annotation, "plain_text": "talic word."},
                ]
        }
    }

    pandoc_output = converter._parse_block(input)
    assert pandoc_output == [Para([Str("An"), Space(),
                                   Emph([Str("i")]), Str("talic"), Space(), Str("word.")])]

    markdown_output = pandoc.write(pandoc_output)
    expected_markdown = "An *i*talic word.\r\n"
    assert markdown_output == expected_markdown


def test_bold_italic_word():
    input = {
        "type": "paragraph",
        "has_children": False,
        "paragraph": {
                "text": [
                    {"annotations": default_annotation, "plain_text": "A "},
                    {"annotations": {"bold": True, "italic": True, "strikethrough": False,
                                     "underline": False, "code": False, "color": "default"},
                        "plain_text": "bold-italic"},
                    {"annotations": default_annotation, "plain_text": " word."},
                ]
        }
    }

    pandoc_output = converter._parse_block(input)
    assert pandoc_output == [Para([Str("A"), Space(), Emph([Strong([Str("bold-italic")])]),
                                   Space(), Str("word.")])]

    markdown_output = pandoc.write(pandoc_output)
    expected_markdown = "A ***bold-italic*** word.\r\n"
    assert markdown_output == expected_markdown


def test_strikeout_word():
    input = {
        "type": "paragraph",
        "has_children": False,
        "paragraph": {
                "text": [
                    {"annotations": default_annotation, "plain_text": "A "},
                    {"annotations": {"bold": False, "italic": False, "strikethrough": True,
                                     "underline": False, "code": False, "color": "default"},
                        "plain_text": "deleted"},
                    {"annotations": default_annotation, "plain_text": " word."},
                ]
        }
    }

    pandoc_output = converter._parse_block(input)
    assert pandoc_output == [
        Para([Str("A"), Space(), Strikeout([Str("deleted")]), Space(), Str("word.")])]

    markdown_output = pandoc.write(pandoc_output)
    expected_markdown = "A ~~deleted~~ word.\r\n"
    assert markdown_output == expected_markdown


def test_code_inline():
    input = {
        "type": "paragraph",
        "has_children": False,
        "paragraph": {
                "text": [
                    {"annotations": default_annotation, "plain_text": "A "},
                    {"annotations": {"bold": False, "italic": False, "strikethrough": False,
                                     "underline": False, "code": True, "color": "default"},
                        "plain_text": "code"},
                    {"annotations": default_annotation, "plain_text": " word."},
                ]
        }
    }

    pandoc_output = converter._parse_block(input)
    assert pandoc_output == [
        Para([Str("A"), Space(), Code(("", [], []), "code"), Space(), Str("word.")])]

    markdown_output = pandoc.write(pandoc_output)
    expected_markdown = "A `code` word.\r\n"
    assert markdown_output == expected_markdown

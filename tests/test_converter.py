import pytest
from n2y import converter
import pandoc
from pandoc.types import Str, Para, Plain, Space, Header, Strong, Emph, Strikeout,\
    Code, BulletList, OrderedList, Decimal, Period, Meta, Pandoc, Link, HorizontalRule

import json
from os.path import join, dirname

default_annotation = {"bold": False, "italic": False, "strikethrough": False,
                      "underline": False, "code": False, "color": "default"}


def newline_lf(input):
    return input.replace('\r\n', '\n')


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
                         "href": None,
                         "plain_text": "paragraph text"}
                 ]}}

    pandoc_output = converter._parse_block(input)
    assert pandoc_output == [Para([Str("paragraph"), Space(), Str("text")])]

    markdown_output = pandoc.write(pandoc_output, format='gfm')
    assert newline_lf(markdown_output) == "paragraph text\n"


def test_parse_heading_1():
    input = {"type": "heading_1",
             "has_children": False,
             "heading_1": {
                 "text": [
                     {
                         "annotations": default_annotation,
                         "href": None,
                         "plain_text": "Heading One"}
                 ]}}

    pandoc_output = converter._parse_block(input)
    assert pandoc_output == [Header(1, ("", [], []), [Str("Heading"), Space(), Str("One")])]

    markdown_output = pandoc.write(pandoc_output, format='gfm')
    assert newline_lf(markdown_output) == "# Heading One\n"


def test_parse_heading_2():
    input = {"type": "heading_2",
             "has_children": False,
             "heading_2": {
                 "text": [
                     {
                         "annotations": default_annotation,
                         "href": None,
                         "plain_text": "Heading Two"}
                 ]}}

    pandoc_output = converter._parse_block(input)
    assert pandoc_output == [Header(2, ("", [], []), [Str("Heading"), Space(), Str("Two")])]

    markdown_output = pandoc.write(pandoc_output, format='gfm')
    assert newline_lf(markdown_output) == "## Heading Two\n"


def test_parse_heading_3():
    input = {"type": "heading_3",
             "has_children": False,
             "heading_3": {
                 "text": [
                     {
                         "annotations": default_annotation,
                         "href": None,
                         "plain_text": "Heading Three"}
                 ]}}

    pandoc_output = converter._parse_block(input)
    assert pandoc_output == [Header(3, ("", [], []), [Str("Heading"), Space(), Str("Three")])]

    markdown_output = pandoc.write(pandoc_output, format='gfm')
    assert newline_lf(markdown_output) == "### Heading Three\n"


def test_bulleted_list():
    input = {"type": "paragraph",
             "has_children": True,
             "paragraph": {
                 "has_children": True,
                 "text": [
                     {
                         "annotations": default_annotation,
                         "href": None,
                         "plain_text": "Bulleted List"}
                 ]},
             "children": [
                 {
                     "type": "bulleted_list_item",
                     "has_children": False,
                     "bulleted_list_item": {
                         "text": [{
                             "annotations": default_annotation,
                             "href": None,
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
                             "href": None,
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

    markdown_output = pandoc.write(pandoc_output, format='gfm')
    expected_markdown = "Bulleted List\n\n-   Item One\n-   Item Two\n"
    assert newline_lf(markdown_output) == expected_markdown


def test_numbered_list():
    input = {"type": "paragraph",
             "has_children": True,
             "paragraph": {
                 "has_children": True,
                 "text": [
                     {
                         "annotations": default_annotation,
                         "href": None,
                         "plain_text": "Numbered List"}
                 ]},
             "children": [
                 {
                     "type": "numbered_list_item",
                     "has_children": False,
                     "numbered_list_item": {
                         "text": [{
                             "annotations": default_annotation,
                             "href": None,
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
                             "href": None,
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

    markdown_output = pandoc.write(pandoc_output, format='gfm')
    expected_markdown = "Numbered List\n\n1.  Item One\n2.  Item Two\n"
    assert newline_lf(markdown_output) == expected_markdown


def test_numbered_and_bulleted_list():
    input = {"type": "paragraph",
             "has_children": True,
             "paragraph": {
                 "has_children": True,
                 "text": [
                     {
                         "annotations": default_annotation,
                         "href": None,
                         "plain_text": "Mixed List"}
                 ]},
             "children": [
                 {
                     "type": "numbered_list_item",
                     "has_children": False,
                     "numbered_list_item": {
                         "text": [{
                             "annotations": default_annotation,
                             "href": None,
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
                             "href": None,
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
                             "href": None,
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
                             "href": None,
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

    markdown_output = pandoc.write(pandoc_output, format='gfm')
    expected_markdown = (
        "Mixed List\n"
        "\n"
        "1.  Item One\n"
        "\n"
        "-   Bulleted item\n"
        "\n"
        "1.  Item Two\n"
        "\n"
        "-   Bulleted item two\n")

    assert newline_lf(markdown_output) == expected_markdown


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

    markdown_output = pandoc.write(pandoc_output, format='gfm')
    expected_markdown = (
        "1.  item one\n"
        "    1.  sub item one\n"
        "        -   bulleted item one\n"
        "        -   bulleted item one\n"
        "            skip bullet\n"
        "    2.  subitem two\n"
        "        skip number\n"
        "2.  item two\n"
        "\n"
        "Paragraph after a numbered list\n")
    assert newline_lf(markdown_output) == expected_markdown


def test_convert():
    input = {"type": "page",
             "content": [
                 {
                     "type": "paragraph",
                     "has_children": False,
                     "paragraph": {
                         "text": [
                             {"annotations": default_annotation,
                              "href": None,
                              "plain_text": "Simple page"},
                         ]
                     }
                 }, ]
             }
    pandoc_output = converter.convert(input)
    assert pandoc_output == Pandoc(Meta({}), [Para([Str("Simple"), Space(), Str("page")])])

    markdown_output = pandoc.write(pandoc_output, format='gfm')
    expected_markdown = "Simple page\n"
    assert newline_lf(markdown_output) == expected_markdown


def test_bold_word():
    input = {
        "type": "paragraph",
        "has_children": False,
        "paragraph": {
                "text": [
                    {"annotations": default_annotation, "href": None, "plain_text": "A "},
                    {"annotations": {"bold": True, "italic": False, "strikethrough": False,
                                     "underline": False, "code": False, "color": "default"},
                        "href": None,
                        "plain_text": "bold"},
                    {"annotations": default_annotation, "href": None, "plain_text": " word."},
                ]
        }
    }

    pandoc_output = converter._parse_block(input)
    assert pandoc_output == [Para([Str("A"), Space(),
                                   Strong([Str("bold")]), Space(), Str("word.")])]

    markdown_output = pandoc.write(pandoc_output, format='gfm')
    expected_markdown = "A **bold** word.\n"
    assert newline_lf(markdown_output) == expected_markdown


def test_bold_letter():
    input = {
        "type": "paragraph",
        "has_children": False,
        "paragraph": {
                "text": [
                    {"annotations": default_annotation, "href": None, "plain_text": "A "},
                    {"annotations": {"bold": True, "italic": False, "strikethrough": False,
                                     "underline": False, "code": False, "color": "default"},
                        "href": None,
                        "plain_text": "b"},
                    {"annotations": default_annotation, "href": None, "plain_text": "old word."},
                ]
        }
    }

    pandoc_output = converter._parse_block(input)
    assert pandoc_output == [Para([Str("A"), Space(),
                                   Strong([Str("b")]), Str("old"), Space(), Str("word.")])]

    markdown_output = pandoc.write(pandoc_output, format='gfm')
    expected_markdown = "A **b**old word.\n"
    assert newline_lf(markdown_output) == expected_markdown


def test_italic_word():
    input = {
        "type": "paragraph",
        "has_children": False,
        "paragraph": {
                "text": [
                    {"annotations": default_annotation, "href": None, "plain_text": "An "},
                    {"annotations": {"bold": False, "italic": True, "strikethrough": False,
                                     "underline": False, "code": False, "color": "default"},
                        "href": None,
                        "plain_text": "italic"},
                    {"annotations": default_annotation, "href": None, "plain_text": " word."},
                ]
        }
    }

    pandoc_output = converter._parse_block(input)
    assert pandoc_output == [Para([Str("An"), Space(),
                                   Emph([Str("italic")]), Space(), Str("word.")])]

    markdown_output = pandoc.write(pandoc_output, format='gfm')
    expected_markdown = "An *italic* word.\n"
    assert newline_lf(markdown_output) == expected_markdown


def test_italic_letter():
    input = {
        "type": "paragraph",
        "has_children": False,
        "paragraph": {
                "text": [
                    {"annotations": default_annotation, "href": None, "plain_text": "An "},
                    {"annotations": {"bold": False, "italic": True, "strikethrough": False,
                                     "underline": False, "code": False, "color": "default"},
                        "href": None,
                        "plain_text": "i"},
                    {"annotations": default_annotation, "href": None, "plain_text": "talic word."},
                ]
        }
    }

    pandoc_output = converter._parse_block(input)
    assert pandoc_output == [Para([Str("An"), Space(),
                                   Emph([Str("i")]), Str("talic"), Space(), Str("word.")])]

    markdown_output = pandoc.write(pandoc_output, format='gfm')
    expected_markdown = "An *i*talic word.\n"
    assert newline_lf(markdown_output) == expected_markdown


def test_bold_italic_word():
    input = {
        "type": "paragraph",
        "has_children": False,
        "paragraph": {
                "text": [
                    {"annotations": default_annotation, "href": None, "plain_text": "A "},
                    {"annotations": {"bold": True, "italic": True, "strikethrough": False,
                                     "underline": False, "code": False, "color": "default"},
                        "href": None,
                        "plain_text": "bold-italic"},
                    {"annotations": default_annotation, "href": None, "plain_text": " word."},
                ]
        }
    }

    pandoc_output = converter._parse_block(input)
    assert pandoc_output == [Para([Str("A"), Space(), Emph([Strong([Str("bold-italic")])]),
                                   Space(), Str("word.")])]

    markdown_output = pandoc.write(pandoc_output, format='gfm')
    expected_markdown = "A ***bold-italic*** word.\n"
    assert newline_lf(markdown_output) == expected_markdown


def test_strikeout_word():
    input = {
        "type": "paragraph",
        "has_children": False,
        "paragraph": {
                "text": [
                    {"annotations": default_annotation, "href": None, "plain_text": "A "},
                    {"annotations": {"bold": False, "italic": False, "strikethrough": True,
                                     "underline": False, "code": False, "color": "default"},
                        "href": None,
                        "plain_text": "deleted"},
                    {"annotations": default_annotation, "href": None, "plain_text": " word."},
                ]
        }
    }

    pandoc_output = converter._parse_block(input)
    assert pandoc_output == [
        Para([Str("A"), Space(), Strikeout([Str("deleted")]), Space(), Str("word.")])]

    markdown_output = pandoc.write(pandoc_output, format='gfm')
    expected_markdown = "A ~~deleted~~ word.\n"
    assert newline_lf(markdown_output) == expected_markdown


def test_code_inline():
    input = {
        "type": "paragraph",
        "has_children": False,
        "paragraph": {
                "text": [
                    {"annotations": default_annotation, "href": None, "plain_text": "A "},
                    {"annotations": {"bold": False, "italic": False, "strikethrough": False,
                                     "underline": False, "code": True, "color": "default"},
                        "href": None,
                        "plain_text": "code"},
                    {"annotations": default_annotation, "href": None, "plain_text": " word."},
                ]
        }
    }

    pandoc_output = converter._parse_block(input)
    assert pandoc_output == [
        Para([Str("A"), Space(), Code(("", [], []), "code"), Space(), Str("word.")])]

    markdown_output = pandoc.write(pandoc_output, format='gfm')
    expected_markdown = "A `code` word.\n"
    assert newline_lf(markdown_output) == expected_markdown


def test_link_inline():
    input = {
        "type": "paragraph",
        "has_children": False,
        "paragraph": {
                "text": [
                    {"annotations": default_annotation, "href": None, "plain_text": "A "},
                    {"annotations": {"bold": False, "italic": False, "strikethrough": False,
                                     "underline": False, "code": False, "color": "default"},
                        "href": "https://innolitics.com/",
                        "plain_text": "link"},
                    {"annotations": default_annotation, "href": None, "plain_text": " word."},
                ]
        }
    }

    pandoc_output = converter._parse_block(input)
    assert pandoc_output == [
        Para([Str('A'), Space(), Link(('', [], []), [Str('link')], ('https://innolitics.com/', '')),
              Space(), Str('word.')])]

    markdown_output = pandoc.write(pandoc_output, format='gfm')
    expected_markdown = "A [link](https://innolitics.com/) word.\n"
    assert newline_lf(markdown_output) == expected_markdown


def test_bookmark_with_caption():
    input = {
        "type": "bookmark",
        "has_children": False,
        "bookmark": {
            "caption": [
                {"annotations": default_annotation,
                 "href": None,
                 "plain_text": "Innolitics"}],
            "url": "https://innolotics.com"
        }
    }

    pandoc_output = converter._parse_block(input)
    assert pandoc_output == \
        [Para([Link(('', [], []), [Str('Innolitics')], ('https://innolotics.com', ''))])]

    markdown_output = pandoc.write(pandoc_output, format='gfm')
    expected_markdown = "[Innolitics](https://innolotics.com)\n"
    assert newline_lf(markdown_output) == expected_markdown


def test_bookmark_without_caption():
    input = {
        "type": "bookmark",
        "has_children": False,
        "bookmark": {
            "caption": [],
            "url": "https://innolotics.com"
        }
    }

    pandoc_output = converter._parse_block(input)
    assert pandoc_output == \
        [Para([Link(('', [], []), [Str('https://innolotics.com')],
                    ('https://innolotics.com', ''))])]

    markdown_output = pandoc.write(pandoc_output, format='gfm')
    expected_markdown = "<https://innolotics.com>\n"
    assert newline_lf(markdown_output) == expected_markdown


def test_divider():
    input = {
        "type": "divider",
        "has_children": False
    }

    pandoc_output = converter._parse_block(input)
    assert pandoc_output == [HorizontalRule()]

    markdown_output = pandoc.write(pandoc_output, format='gfm')
    expected_markdown = "------------------------------------------------------------------------\n"
    assert newline_lf(markdown_output) == expected_markdown

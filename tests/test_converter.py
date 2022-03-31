from unittest import mock

import pytest
import pandoc
from pandoc.types import Str, Para, Plain, Space, Header, Strong, Emph, \
    Strikeout, Code, CodeBlock, BulletList, OrderedList, Decimal, Period, Meta, Pandoc, Link, \
    HorizontalRule, BlockQuote, Image, MetaString, Table, TableHead, TableBody, \
    TableFoot, RowHeadColumns, Row, Cell, RowSpan, ColSpan, ColWidthDefault, AlignDefault, \
    Caption, Math, InlineMath, DisplayMath, Underline

from n2y import converter, notion

default_annotation = {
    "bold": False, "italic": False, "strikethrough": False,
    "underline": False, "code": False, "color": "default"}

eq1 = "{\\displaystyle i\\hbar {\\frac {d}{dt}}\\vert "
eq2 = "\\Psi (t)\\rangle={\\hat {H}}\\vert \\Psi (t)\\rangle}"
default_equation = f"{eq1}{eq2}"


def generate_annotated_obj(arr):
    obj = {
        'object': 'block',
        'has_children': False,
        'archived': False,
        'type': 'paragraph',
        'paragraph': {
            'color': 'default',
            'text': []}}
    for block in arr:
        text_block = {
            'type': 'text',
            'text': {'content': block[0], 'link': None},
            'annotations': {
                'bold': True if 'bold' in block[1] else False,
                'italic': True if 'italic' in block[1] else False,
                'strikethrough': True if 'strikethrough' in block[1] else False,
                'underline': True if 'underline' in block[1] else False,
                'code': True if 'code' in block[1] else False,
                'color': 'default'},
            'plain_text': block[0],
            'href': None}
        obj['paragraph']['text'].append(text_block)
    return obj


def newline_lf(input):
    return input.replace('\r\n', '\n')


@mock.patch.object(notion.Client, 'get_block')
def test_unknown_block_type(mock_get_block):
    mock_get_block.return_value = {"type": "this does not exist"}
    client = notion.Client('')
    with pytest.raises(NotImplementedError):
        converter.load_block(client, None)


@mock.patch.object(notion.Client, 'get_block')
def test_paragraph(mock_get_block):
    input = {
        "type": "paragraph",
        "has_children": False,
        "paragraph": {
            "text": [
                {
                    "type": "text",
                    "annotations": default_annotation,
                    "href": None,
                    "plain_text": "paragraph text"}]}}
    mock_get_block.return_value = input
    client = notion.Client('')
    paragraph_object = converter.load_block(client, None)
    pandoc_output = paragraph_object.to_pandoc()
    assert pandoc_output == Para([Str("paragraph"), Space(), Str("text")])
    markdown_output = pandoc.write(pandoc_output, format='gfm')
    assert newline_lf(markdown_output) == "paragraph text\n"


@mock.patch.object(notion.Client, 'get_block')
def test_heading_1(mock_get_block):
    input = {
        "type": "heading_1",
        "has_children": False,
        "heading_1": {
            "text": [
                {
                    "type": "text",
                    "annotations": default_annotation,
                    "href": None,
                    "plain_text": "Heading One"}]}}
    mock_get_block.return_value = input
    client = notion.Client('')
    heading_object = converter.load_block(client, None)
    pandoc_output = heading_object.to_pandoc()
    assert pandoc_output == Header(1, ("", [], []), [Str("Heading"), Space(), Str("One")])
    markdown_output = pandoc.write(pandoc_output, format='gfm')
    assert newline_lf(markdown_output) == "# Heading One\n"


@mock.patch.object(notion.Client, 'get_block')
def test_heading_2(mock_get_block):
    input = {
        "type": "heading_2",
        "has_children": False,
        "heading_2": {
            "text": [
                {
                    "type": "text",
                    "annotations": default_annotation,
                    "href": None,
                    "plain_text": "Heading One"}]}}
    mock_get_block.return_value = input
    client = notion.Client('')
    heading_object = converter.load_block(client, None)
    pandoc_output = heading_object.to_pandoc()
    assert pandoc_output == Header(2, ("", [], []), [Str("Heading"), Space(), Str("One")])
    markdown_output = pandoc.write(pandoc_output, format='gfm')
    assert newline_lf(markdown_output) == "## Heading One\n"


@mock.patch.object(notion.Client, 'get_block')
def test_heading_3(mock_get_block):
    input = {
        "type": "heading_3",
        "has_children": False,
        "heading_3": {
            "text": [
                {
                    "type": "text",
                    "annotations": default_annotation,
                    "href": None,
                    "plain_text": "Heading One"}]}}
    mock_get_block.return_value = input
    client = notion.Client('')
    heading_object = converter.load_block(client, None)
    pandoc_output = heading_object.to_pandoc()
    assert pandoc_output == Header(3, ("", [], []), [Str("Heading"), Space(), Str("One")])
    markdown_output = pandoc.write(pandoc_output, format='gfm')
    assert newline_lf(markdown_output) == "### Heading One\n"


@mock.patch.object(notion.Client, 'get_block_children')
@mock.patch.object(notion.Client, 'get_block')
def test_bulleted_list(mock_get_block, mock_get_block_children):
    input = {
        "type": "paragraph",
        "has_children": True,
        "id": None,
        "paragraph": {
            "has_children": True,
            "text": [{
                "type": "text",
                "annotations": default_annotation,
                "href": None,
                "plain_text": "Bulleted List"}]}}
    children = [
        {
            "type": "bulleted_list_item",
            "has_children": False,
            "bulleted_list_item": {
                "text": [{
                    "type": "text",
                    "annotations": default_annotation,
                    "href": None,
                    "plain_text": "Item One"}]}},
        {
            "type": "bulleted_list_item",
            "has_children": False,
            "bulleted_list_item": {
                "text": [{
                    "type": "text",
                    "annotations": default_annotation,
                    "href": None,
                    "plain_text": "Item Two"}]}}]
    mock_get_block.return_value = input
    mock_get_block_children.return_value = children
    client = notion.Client('')
    bulleted_list_object = converter.load_block(client, None)
    pandoc_output = bulleted_list_object.to_pandoc()
    assert pandoc_output == [
        Para([Str("Bulleted"), Space(), Str("List")]),
        BulletList([
            [Plain([Str("Item"), Space(), Str("One")])],
            [Plain([Str("Item"), Space(), Str("Two")])]])]
    markdown_output = pandoc.write(pandoc_output, format='gfm')
    expected_markdown = "Bulleted List\n\n-   Item One\n-   Item Two\n"
    assert newline_lf(markdown_output) == expected_markdown


@mock.patch.object(notion.Client, 'get_block_children')
@mock.patch.object(notion.Client, 'get_block')
def test_numbered_list(mock_get_block, mock_get_block_children):
    input = {
        "type": "paragraph",
        "has_children": True,
        "id": None,
        "paragraph": {
            "has_children": True,
            "text": [
                {
                    "type": "text",
                    "annotations": default_annotation,
                    "href": None,
                    "plain_text": "Numbered List"}]}}
    children = [
        {
            "type": "numbered_list_item",
            "has_children": False,
            "numbered_list_item": {
                "text": [{
                    "type": "text",
                    "annotations": default_annotation,
                    "href": None,
                    "plain_text": "Item One"}]}},
        {
            "type": "numbered_list_item",
            "has_children": False,
            "numbered_list_item": {
                "text": [{
                    "type": "text",
                    "annotations": default_annotation,
                    "href": None,
                    "plain_text": "Item Two"}]}}]
    mock_get_block.return_value = input
    mock_get_block_children.return_value = children
    client = notion.Client('')
    numbered_list_object = converter.load_block(client, None)
    pandoc_output = numbered_list_object.to_pandoc()
    assert pandoc_output == [
        Para([Str("Numbered"), Space(), Str("List")]),
        OrderedList(
            (1, Decimal(), Period()),
            [
                [Plain([Str("Item"), Space(), Str("One")])],
                [Plain([Str("Item"), Space(), Str("Two")])]])]
    markdown_output = pandoc.write(pandoc_output, format='gfm')
    expected_markdown = "Numbered List\n\n1.  Item One\n2.  Item Two\n"
    assert newline_lf(markdown_output) == expected_markdown


@mock.patch.object(notion.Client, 'get_block_children')
@mock.patch.object(notion.Client, 'get_block')
def test_page(mock_get_block, mock_get_block_children):
    input = {
        "type": "child_page",
        "has_children": True,
        "id": None,
        "child_page": {"title": "Simple Page"}}
    children = [{
        "type": "paragraph",
        'id': None,
        "has_children": False,
        "paragraph": {
            "text": [{
                "type": "text",
                "annotations": default_annotation,
                "href": None,
                "plain_text": "Simple page"}]}}]
    mock_get_block.return_value = input
    mock_get_block_children.return_value = children
    client = notion.Client('')
    child_page_object = converter.load_block(client, None)
    pandoc_output = child_page_object.to_pandoc()
    assert pandoc_output == Pandoc(
        Meta({'title': MetaString('Simple Page')}),
        [Para([Str("Simple"), Space(), Str("page")])])
    markdown_output = pandoc.write(pandoc_output, format='gfm')
    expected_markdown = "Simple page\n"
    assert newline_lf(markdown_output) == expected_markdown


def test_bold_word():
    input = generate_annotated_obj([('A ', []), ('bold', ['bold']), (' word.', [])])
    obj = converter.ParagraphBlock(None, input, get_children=False)
    pandoc_output = obj.to_pandoc()
    assert pandoc_output == Para([
        Str("A"), Space(), Strong([Str("bold")]), Space(), Str("word.")])
    markdown_output = pandoc.write(pandoc_output, format='gfm')
    expected_markdown = "A **bold** word.\n"
    assert newline_lf(markdown_output) == expected_markdown


def test_bold_letter():
    input = generate_annotated_obj([('A ', []), ('b', ['bold']), ('old word.', [])])
    obj = converter.ParagraphBlock(None, input, get_children=False)
    pandoc_output = obj.to_pandoc()
    assert pandoc_output == Para(
        [Str("A"), Space(), Strong([Str("b")]), Str("old"), Space(), Str("word.")])
    markdown_output = pandoc.write(pandoc_output, format='gfm')
    expected_markdown = "A **b**old word.\n"
    assert newline_lf(markdown_output) == expected_markdown


def test_italic_word():
    input = generate_annotated_obj([('An ', []), ('italic', ['italic']), (' word.', [])])
    obj = converter.ParagraphBlock(None, input, get_children=False)
    pandoc_output = obj.to_pandoc()
    assert pandoc_output == Para(
        [Str("An"), Space(), Emph([Str("italic")]), Space(), Str("word.")])
    markdown_output = pandoc.write(pandoc_output, format='gfm')
    expected_markdown = "An *italic* word.\n"
    assert newline_lf(markdown_output) == expected_markdown


def test_italic_letter():
    input = generate_annotated_obj([('An ', []), ('i', ['italic']), ('talic word.', [])])
    obj = converter.ParagraphBlock(None, input, get_children=False)
    pandoc_output = obj.to_pandoc()
    assert pandoc_output == Para(
        [Str("An"), Space(), Emph([Str("i")]), Str("talic"), Space(), Str("word.")])
    markdown_output = pandoc.write(pandoc_output, format='gfm')
    expected_markdown = "An *i*talic word.\n"
    assert newline_lf(markdown_output) == expected_markdown


def test_bold_italic_word():
    input = generate_annotated_obj([
        ('A ', []),
        ('bold-italic', ['bold', 'italic']),
        (' word.', [])])
    obj = converter.ParagraphBlock(None, input, get_children=False)
    pandoc_output = obj.to_pandoc()
    assert pandoc_output == Para([
        Str('A'),
        Space(),
        Strong([Emph([Str('bold-italic')])]),
        Space(),
        Str('word.')])
    markdown_output = pandoc.write(pandoc_output, format='gfm')
    expected_markdown = "A ***bold-italic*** word.\n"
    assert newline_lf(markdown_output) == expected_markdown


def test_strikeout_word():
    input = generate_annotated_obj([('A ', []), ('deleted', ['strikethrough']), (' word.', [])])
    obj = converter.ParagraphBlock(None, input, get_children=False)
    pandoc_output = obj.to_pandoc()
    assert pandoc_output == Para(
        [Str("A"), Space(), Strikeout([Str("deleted")]), Space(), Str("word.")])
    markdown_output = pandoc.write(pandoc_output, format='gfm')
    expected_markdown = "A ~~deleted~~ word.\n"
    assert newline_lf(markdown_output) == expected_markdown


def test_annotated_spaces():
    input = generate_annotated_obj([
        ('this ', ['bold']),
        ('is ', ['bold', 'italic']),
        ('a', ['italic']),
        (' test', ['strikethrough']),
        (' did', ['bold', 'underline', 'code']),
        (' i pass', ['underline', 'code']),
        ('?', [])])
    obj = converter.ParagraphBlock(None, input, get_children=False)
    pandoc_output = obj.to_pandoc()
    assert pandoc_output == Para([
        Strong([Str('this')]),
        Space(),
        Strong([Emph([Str('is')])]),
        Space(),
        Emph([Str('a')]),
        Space(),
        Strikeout([Str('test')]),
        Underline([Strong([Code(('', [], []), ' did')])]),
        Underline([Code(('', [], []), ' i pass')]),
        Str('?')])


def test_equation_inline():
    input = {
        'has_children': False,
        'type': 'paragraph',
        'paragraph': {'text': [
            {
                'type': 'text',
                'text': {
                    'content': 'Schrödinger Equation (',
                    'link': None},
                'annotations': default_annotation,
                'plain_text': 'Schrödinger Equation (',
                'href': None},
            {
                'type': 'equation',
                'equation': {
                    'expression': default_equation
                },
                'annotations': default_annotation,
                'plain_text': default_equation,
                'href': None},
            {
                'type': 'text',
                'text': {
                    'content': ') is a very useful one indeed',
                    'link': None
                },
                'annotations': default_annotation,
                'plain_text': ') is a very useful one indeed',
                'href': None}]}}

    obj = converter.parse_block(None, input, get_children=False)
    pandoc_output = obj.to_pandoc()
    assert pandoc_output == Para([
        Str('Schrödinger'), Space(), Str('Equation'), Space(), Str('('),
        Math(InlineMath(), default_equation), Str(')'), Space(),
        Str('is'), Space(), Str('a'), Space(), Str('very'), Space(),
        Str('useful'), Space(), Str('one'), Space(), Str('indeed')])
    markdown_output = pandoc.write(pandoc_output, format='gfm+tex_math_dollars')
    md1 = "Schrödinger Equation\n(${\\displaystyle i\\hbar "
    md2 = "{\\frac {d}{dt}}\\vert \\Psi (t)\\rangle={\\hat "
    md3 = "{H}}\\vert \\Psi (t)\\rangle}$)\nis a very useful one indeed\n"
    expected_markdown = f"{md1}{md2}{md3}"
    assert newline_lf(markdown_output) == expected_markdown


def test_code_inline():
    input = generate_annotated_obj([('A ', []), ('code', ['code']), (' word.', [])])
    obj = converter.ParagraphBlock(None, input, get_children=False)
    pandoc_output = obj.to_pandoc()
    assert pandoc_output == Para(
        [Str("A"), Space(), Code(("", [], []), "code"), Space(), Str("word.")])
    markdown_output = pandoc.write(pandoc_output, format='gfm')
    expected_markdown = "A `code` word.\n"
    assert newline_lf(markdown_output) == expected_markdown


def test_link_inline():
    input = {
        "type": "paragraph",
        "has_children": False,
        "paragraph": {"text": [
            {
                "type": "text",
                "annotations": default_annotation,
                "plain_text": "This is a "},
            {
                "type": "text",
                "annotations": {
                    "bold": True,
                    "italic": False,
                    "strikethrough": False,
                    "underline": False,
                    "code": False,
                    "color": "default"},
                "plain_text": "link",
                "href": "https://example.com"},
            {
                "type": "text",
                "annotations": default_annotation,
                "plain_text": "."}]}}
    obj = converter.ParagraphBlock(None, input, get_children=False)
    pandoc_output = obj.to_pandoc()
    assert pandoc_output == Para([
        Str('This'), Space(), Str('is'), Space(), Str('a'), Space(),
        Link(('', [], []), [Strong([Str('link')])], ('https://example.com', '')),
        Str('.')])
    markdown_output = pandoc.write(pandoc_output, format='gfm')
    expected_markdown = 'This is a [**link**](https://example.com).\n'
    assert newline_lf(markdown_output) == expected_markdown


def test_bookmark_with_caption():
    input = {
        "type": "bookmark",
        "has_children": False,
        "bookmark": {
            "caption": [{
                "type": "text",
                "annotations": default_annotation,
                "href": None,
                "plain_text": "Innolitics"}],
            "url": "https://innolotics.com"}}
    obj = converter.parse_block(None, input, get_children=False)
    pandoc_output = obj.to_pandoc()
    assert pandoc_output == Para(
        [Link(('', [], []), [Str('Innolitics')], ('https://innolotics.com', ''))])
    markdown_output = pandoc.write(pandoc_output, format='gfm')
    expected_markdown = "[Innolitics](https://innolotics.com)\n"
    assert newline_lf(markdown_output) == expected_markdown


def test_bookmark_without_caption():
    input = {
        "type": "bookmark",
        "has_children": False,
        "bookmark": {
            "caption": [],
            "url": "https://innolotics.com"}}
    obj = converter.parse_block(None, input, get_children=False)
    pandoc_output = obj.to_pandoc()
    assert pandoc_output == Para(
        [Link(('', [], []), [Str('https://innolotics.com')], ('https://innolotics.com', ''))])
    markdown_output = pandoc.write(pandoc_output, format='gfm')
    expected_markdown = "<https://innolotics.com>\n"
    assert newline_lf(markdown_output) == expected_markdown


def test_divider():
    input = {
        "type": "divider",
        "has_children": False,
        "divider": {}}
    obj = converter.parse_block(None, input, get_children=False)
    pandoc_output = obj.to_pandoc()
    assert pandoc_output == HorizontalRule()
    markdown_output = pandoc.write(pandoc_output, format='gfm')
    expected_markdown = "------------------------------------------------------------------------\n"
    assert newline_lf(markdown_output) == expected_markdown


def test_block_quote():
    input = {
        "type": "quote",
        "has_children": False,
        "quote": {
            "text": [{"type": "text", "annotations": default_annotation, "href": None, "plain_text":
                      "In a time of deceit telling the truth is a revolutionary act."}]
        }
    }

    obj = converter.parse_block(None, input, get_children=False)
    pandoc_output = obj.to_pandoc()

    assert pandoc_output == BlockQuote(
        [Para([Str('In'), Space(), Str('a'), Space(), Str('time'), Space(), Str('of'),
              Space(), Str('deceit'), Space(), Str('telling'), Space(), Str('the'), Space(),
              Str('truth'), Space(), Str('is'), Space(), Str('a'), Space(),
              Str('revolutionary'), Space(), Str('act.')])])

    markdown_output = pandoc.write(pandoc_output, format='gfm')
    expected_markdown = "> In a time of deceit telling the truth is a revolutionary act.\n"
    assert newline_lf(markdown_output) == expected_markdown


@mock.patch.object(converter.File, 'download')
def test_image_internal_with_caption(mock_download):
    input = {
        "type": "image",
        "image": {
            'type': 'file',
            'caption': [
                {"type": "text",
                 "annotations": default_annotation,
                 "href": None,
                 "plain_text": "test image"}],
            'file': {
                'url': "https://example.com/image.png",
                'expiry_time': None
            }
        }
    }

    mock_download.return_value = 'image.png'

    obj = converter.parse_block(None, input, get_children=False)
    pandoc_output = obj.to_pandoc()

    assert pandoc_output == Para([Image(('', [], []), [Str('test'), Space(), Str('image')],
                                        ('image.png', ''))])

    markdown_output = pandoc.write(pandoc_output, format='gfm')
    expected_markdown = "![test image](image.png)\n"
    assert newline_lf(markdown_output) == expected_markdown


def test_image_external_without_caption():
    input = {
        "type": "image",
        "image": {
            'type': 'external',
            'caption': [
                {"type": "text",
                 "annotations": default_annotation,
                 "href": None,
                 "plain_text": "test image"}],
            'external': {
                'url': "https://example.com/image.png",
                # 'expiry_time': None
            }
        }
    }

    obj = converter.parse_block(None, input, get_children=False)
    pandoc_output = obj.to_pandoc()

    assert pandoc_output == Para([Image(('', [], []), [Str('test'), Space(), Str('image')],
                                        ('https://example.com/image.png', ''))])

    markdown_output = pandoc.write(pandoc_output, format='gfm')
    expected_markdown = "![test image](https://example.com/image.png)\n"
    assert newline_lf(markdown_output) == expected_markdown


def test_equation_block():
    input = {
        'type': 'equation',
        'equation': {
            'expression': default_equation}}
    obj = converter.parse_block(None, input, get_children=False)
    pandoc_output = obj.to_pandoc()
    assert pandoc_output == Para(
        [Math(DisplayMath(), default_equation)])
    markdown_output = pandoc.write(pandoc_output, format='gfm+tex_math_dollars')
    md1 = "$${\\displaystyle i\\hbar {\\frac {d}{dt}}\\vert \\Psi"
    md2 = " (t)\\rangle={\\hat {H}}\\vert \\Psi (t)\\rangle}$$\n"
    expected_markdown = f"{md1}{md2}"
    assert newline_lf(markdown_output) == expected_markdown


def test_code_block():
    input = {
        "type": "code",
        "code": {
            "text": [{
                "type": "text",
                "plain_text": "const a = 3"}],
            "language": "javascript"}}
    obj = converter.parse_block(None, input, get_children=False)
    pandoc_output = obj.to_pandoc()
    assert pandoc_output == CodeBlock(('', ['javascript'], []), 'const a = 3')
    markdown_output = pandoc.write(pandoc_output, format='gfm')
    expected_markdown = "``` javascript\nconst a = 3\n```\n"
    assert newline_lf(markdown_output) == expected_markdown


@mock.patch.object(notion.Client, 'get_block_children')
def test_table_block(mock_get_block_children):
    input = {
        'type': 'table',
        'id': None,
        'has_children': True,
        "table": {
            "table_width": 2,
            "has_column_header": True,
            "has_row_header": False}}
    children = [
        {
            "type": "table_row",
            "has_children": False,
            "table_row": {
                "cells": [
                    [{
                        "type": "text",
                        "annotations": default_annotation,
                        "plain_text": "header1",
                        "href": None}],
                    [{
                        "type": "text",
                        "annotations": default_annotation,
                        "plain_text": "header2",
                        "href": None}]]}},
        {
            "type": "table_row",
            "has_children": False,
            "table_row": {
                "cells": [
                    [{
                        "type": "text",
                        "annotations": default_annotation,
                        "plain_text": "one",
                        "href": None}],
                    [{
                        "type": "text",
                        "annotations": default_annotation,
                        "plain_text": "two",
                        "href": None}]]}},
        {
            "type": "table_row",
            "has_children": False,
            "table_row": {
                "cells": [
                    [{
                        "type": "text",
                        "annotations": default_annotation,
                        "plain_text": "three",
                        "href": None}],
                    [{
                        "type": "text",
                        "annotations": default_annotation,
                        "plain_text": "four",
                        "href": None}]]}}]
    mock_get_block_children.return_value = children
    client = notion.Client('')
    obj = converter.parse_block(client, input)
    pandoc_output = obj.to_pandoc()
    assert pandoc_output == Table(
        ('', [], []),
        Caption(None, []),
        [(AlignDefault(), ColWidthDefault()), (AlignDefault(), ColWidthDefault())],
        TableHead(
            ('', [], []),
            [Row(('', [], []), [
                Cell(
                    ('', [], []), AlignDefault(), RowSpan(1),
                    ColSpan(1), [Plain([Str('header1')])]),
                Cell(
                    ('', [], []), AlignDefault(), RowSpan(1),
                    ColSpan(1), [Plain([Str('header2')])])])]),
        [TableBody(('', [], []), RowHeadColumns(0), [], [
            Row(('', [], []), [
                Cell(
                    ('', [], []), AlignDefault(), RowSpan(1),
                    ColSpan(1), [Plain([Str('one')])]),
                Cell(
                    ('', [], []), AlignDefault(), RowSpan(1),
                    ColSpan(1), [Plain([Str('two')])])]),
            Row(('', [], []), [
                Cell(
                    ('', [], []), AlignDefault(), RowSpan(1),
                    ColSpan(1), [Plain([Str('three')])]),
                Cell(
                    ('', [], []), AlignDefault(), RowSpan(1),
                    ColSpan(1), [Plain([Str('four')])])])])],
        TableFoot(('', [], []), []))
    markdown_output = pandoc.write(pandoc_output, format='gfm')
    assert newline_lf(markdown_output) == (
        '| header1 | header2 |\n'
        '|---------|---------|\n'
        '| one     | two     |\n'
        '| three   | four    |\n')


@mock.patch.object(notion.Client, 'get_block_children')
def test_toggle(mock_get_block_children):
    input = {
        'type': 'toggle',
        'id': None,
        'has_children': True,
        "toggle": {
            "text": [{
                "type": "text",
                "annotations": default_annotation,
                "plain_text": "Toggle Header",
                "href": None}]}}
    children = [{
        "type": "paragraph",
        "has_children": False,
        "paragraph": {
            "text": [{
                "type": "text",
                "annotations": default_annotation,
                "plain_text": "Toggle Content",
                "href": None}]}}]
    mock_get_block_children.return_value = children
    client = notion.Client('')
    obj = converter.parse_block(client, input)
    pandoc_output = obj.to_pandoc()
    assert pandoc_output == BulletList([[
        Para([Str('Toggle'), Space(), Str('Header')]),
        Para([Str('Toggle'), Space(), Str('Content')])]])
    markdown_output = pandoc.write(pandoc_output, format='gfm')
    assert newline_lf(markdown_output) == (
        '-   Toggle Header\n'
        '\n'
        '    Toggle Content\n')


@mock.patch.object(notion.Client, 'get_block_children')
def test_todo(mock_get_block_children):
    input = {
        "type": "paragraph",
        "has_children": True,
        "id": None,
        "paragraph": {
            "text": [{
                "type": "text",
                "annotations": default_annotation,
                "href": None,
                "plain_text": "Task List"}]}}
    children = [
        {
            "type": "to_do",
            "has_children": False,
            "checked": True,
            "to_do": {
                "text": [{
                    "type": "text",
                    "annotations": default_annotation,
                    "href": None,
                    "plain_text": "Task One"}]}},
        {
            "type": "to_do",
            "has_children": False,
            "checked": False,
            "to_do": {
                "text": [{
                    "type": "text",
                    "annotations": default_annotation,
                    "href": None,
                    "plain_text": "Task Two"}]}}]
    mock_get_block_children.return_value = children
    client = notion.Client('')
    obj = converter.parse_block(client, input)
    pandoc_output = obj.to_pandoc()
    assert pandoc_output == [
        Para([Str('Task'), Space(), Str('List')]),
        BulletList([
            [Plain([Str('☒'), Space(), Str('Task'), Space(), Str('One')])],
            [Plain([Str('☐'), Space(), Str('Task'), Space(), Str('Two')])]])]
    markdown_output = pandoc.write(pandoc_output, format='gfm')
    expected_markdown = 'Task List\n\n-   [x] Task One\n-   [ ] Task Two\n'
    assert newline_lf(markdown_output) == expected_markdown

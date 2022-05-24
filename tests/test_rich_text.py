import pandoc
from pandoc.types import (
    Str, Para, Space, Strong, Emph, Strikeout, Code, Link, Math, InlineMath,
    Underline
)

from n2y import blocks
from tests.utils import newline_lf
from tests.notion_mocks import mock_annotations, mock_block, mock_paragraph_block, mock_rich_text


def test_bold_word():
    input = mock_paragraph_block([('A ', []), ('bold', ['bold']), (' word.', [])])
    obj = blocks.ParagraphBlock(None, input, get_children=False)
    pandoc_output = obj.to_pandoc()
    assert pandoc_output == Para([
        Str("A"), Space(), Strong([Str("bold")]), Space(), Str("word.")])
    markdown_output = pandoc.write(pandoc_output, format='gfm')
    expected_markdown = "A **bold** word.\n"
    assert newline_lf(markdown_output) == expected_markdown


def test_bold_letter():
    input = mock_paragraph_block([('A ', []), ('b', ['bold']), ('old word.', [])])
    obj = blocks.ParagraphBlock(None, input, get_children=False)
    pandoc_output = obj.to_pandoc()
    assert pandoc_output == Para(
        [Str("A"), Space(), Strong([Str("b")]), Str("old"), Space(), Str("word.")])
    markdown_output = pandoc.write(pandoc_output, format='gfm')
    expected_markdown = "A **b**old word.\n"
    assert newline_lf(markdown_output) == expected_markdown


def test_bold_spaces():
    input = mock_paragraph_block([(' bold ', ['bold'])])
    obj = blocks.ParagraphBlock(None, input, get_children=False)
    pandoc_output = obj.to_pandoc()
    assert pandoc_output == Para([Space(), Strong([Str('bold')]), Space()])


def test_italic_word():
    input = mock_paragraph_block([('An ', []), ('italic', ['italic']), (' word.', [])])
    obj = blocks.ParagraphBlock(None, input, get_children=False)
    pandoc_output = obj.to_pandoc()
    assert pandoc_output == Para(
        [Str("An"), Space(), Emph([Str("italic")]), Space(), Str("word.")])
    markdown_output = pandoc.write(pandoc_output, format='gfm')
    expected_markdown = "An *italic* word.\n"
    assert newline_lf(markdown_output) == expected_markdown


def test_italic_letter():
    input = mock_paragraph_block([('An ', []), ('i', ['italic']), ('talic word.', [])])
    obj = blocks.ParagraphBlock(None, input, get_children=False)
    pandoc_output = obj.to_pandoc()
    assert pandoc_output == Para(
        [Str("An"), Space(), Emph([Str("i")]), Str("talic"), Space(), Str("word.")])
    markdown_output = pandoc.write(pandoc_output, format='gfm')
    expected_markdown = "An *i*talic word.\n"
    assert newline_lf(markdown_output) == expected_markdown


def test_bold_italic_word():
    input = mock_paragraph_block([
        ('A ', []),
        ('bold-italic', ['bold', 'italic']),
        (' word.', [])])
    obj = blocks.ParagraphBlock(None, input, get_children=False)
    pandoc_output = obj.to_pandoc()
    assert pandoc_output == Para([
        Str('A'),
        Space(),
        Emph([Strong([Str('bold-italic')])]),
        Space(),
        Str('word.')])
    markdown_output = pandoc.write(pandoc_output, format='gfm')
    expected_markdown = "A ***bold-italic*** word.\n"
    assert newline_lf(markdown_output) == expected_markdown


def test_italic_spaces():
    input = mock_paragraph_block([(' italic ', ['italic'])])
    obj = blocks.ParagraphBlock(None, input, get_children=False)
    pandoc_output = obj.to_pandoc()
    assert pandoc_output == Para([Space(), Emph([Str('italic')]), Space()])


def test_strikeout_word():
    input = mock_paragraph_block([('A ', []), ('deleted', ['strikethrough']), (' word.', [])])
    obj = blocks.ParagraphBlock(None, input, get_children=False)
    pandoc_output = obj.to_pandoc()
    assert pandoc_output == Para(
        [Str("A"), Space(), Strikeout([Str("deleted")]), Space(), Str("word.")])
    markdown_output = pandoc.write(pandoc_output, format='gfm')
    expected_markdown = "A ~~deleted~~ word.\n"
    assert newline_lf(markdown_output) == expected_markdown


def test_strikeout_spaces():
    input = mock_paragraph_block([(' strikethrough ', ['strikethrough'])])
    obj = blocks.ParagraphBlock(None, input, get_children=False)
    pandoc_output = obj.to_pandoc()
    assert pandoc_output == Para([Space(), Strikeout([Str('strikethrough')]), Space()])


def test_struckthrough_spaces():
    input1 = mock_paragraph_block([(' strikethrough ', ['strikethrough'])])
    obj1 = blocks.ParagraphBlock(None, input1, get_children=False)
    pandoc_output1 = obj1.to_pandoc()
    assert pandoc_output1 == Para([Space(), Strikeout([Str('strikethrough')]), Space()])


def test_blended_annotated_spaces():
    input = mock_paragraph_block([
        ('this ', ['bold']),
        ('is ', ['bold', 'italic']),
        ('a', ['italic']),
        (' test', ['strikethrough']),
        (' did', ['bold', 'underline', 'code']),
        (' i pass', ['underline', 'code']),
        ('?', [])
    ])
    obj = blocks.ParagraphBlock(None, input, get_children=False)
    pandoc_output = obj.to_pandoc()
    assert pandoc_output == Para([
        Strong([Str('this')]),
        Space(),
        Emph([Strong([Str('is')])]),
        Space(),
        Emph([Str('a')]),
        Space(),
        Strikeout([Str('test')]),
        Underline([Strong([Code(('', [], []), ' did')])]),
        Underline([Code(('', [], []), ' i pass')]),
        Str('?')])


def test_equation_inline():
    lhs = "{\\displaystyle i\\hbar {\\frac {d}{dt}}\\vert "
    rhs = "\\Psi (t)\\rangle={\\hat {H}}\\vert \\Psi (t)\\rangle}"
    example_equation = f"{lhs}{rhs}"

    input = mock_block("paragraph", {'text': [
        mock_rich_text('Schrödinger Equation ('),
        {
            'type': 'equation',
            'equation': {'expression': example_equation},
            'annotations': mock_annotations(),
            'plain_text': example_equation,
            'href': None,
        },
        mock_rich_text(') is a very useful one indeed'),
    ]})

    obj = blocks.ParagraphBlock(None, input, get_children=False)
    pandoc_output = obj.to_pandoc()
    assert pandoc_output == Para([
        Str('Schrödinger'), Space(), Str('Equation'), Space(), Str('('),
        Math(InlineMath(), example_equation), Str(')'), Space(),
        Str('is'), Space(), Str('a'), Space(), Str('very'), Space(),
        Str('useful'), Space(), Str('one'), Space(), Str('indeed')])
    markdown_output = pandoc.write(pandoc_output, format='gfm+tex_math_dollars')
    md1 = "Schrödinger Equation\n(${\\displaystyle i\\hbar "
    md2 = "{\\frac {d}{dt}}\\vert \\Psi (t)\\rangle={\\hat "
    md3 = "{H}}\\vert \\Psi (t)\\rangle}$)\nis a very useful one indeed\n"
    expected_markdown = f"{md1}{md2}{md3}"
    assert newline_lf(markdown_output) == expected_markdown


def test_code_inline():
    input = mock_paragraph_block([('A ', []), ('code', ['code']), (' word.', [])])
    obj = blocks.ParagraphBlock(None, input, get_children=False)
    pandoc_output = obj.to_pandoc()
    assert pandoc_output == Para(
        [Str("A"), Space(), Code(("", [], []), "code"), Space(), Str("word.")])
    markdown_output = pandoc.write(pandoc_output, format='gfm')
    expected_markdown = "A `code` word.\n"
    assert newline_lf(markdown_output) == expected_markdown


def test_link_inline():
    input = mock_block("paragraph", {"text": [
        mock_rich_text("This is a "),
        mock_rich_text("link", ["bold"], href="https://example.com"),
        mock_rich_text("."),
    ]})
    obj = blocks.ParagraphBlock(None, input, get_children=False)
    pandoc_output = obj.to_pandoc()
    assert pandoc_output == Para([
        Str('This'), Space(), Str('is'), Space(), Str('a'), Space(),
        Link(('', [], []), [Strong([Str('link')])], ('https://example.com', '')),
        Str('.')])
    markdown_output = pandoc.write(pandoc_output, format='gfm')
    expected_markdown = 'This is a [**link**](https://example.com).\n'
    assert newline_lf(markdown_output) == expected_markdown

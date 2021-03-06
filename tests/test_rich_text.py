from pandoc.types import (
    Str, Space, Strong, Emph, Strikeout, Code, Link, Math, InlineMath,
    Underline
)

from n2y.notion import Client
from tests.notion_mocks import mock_rich_text_array, mock_annotations, mock_rich_text


def process_rich_text_array(notion_data):
    client = Client('')
    rich_text_array = client.wrap_notion_rich_text_array(notion_data)
    pandoc_ast = rich_text_array.to_pandoc()
    markdown = rich_text_array.to_markdown()
    plain_text = rich_text_array.to_plain_text()
    return pandoc_ast, markdown, plain_text


def test_bold_word():
    notion_data = mock_rich_text_array([('A ', []), ('bold', ['bold']), (' word.', [])])
    pandoc_ast, markdown, plain_text = process_rich_text_array(notion_data)
    assert pandoc_ast == [
        Str("A"), Space(), Strong([Str("bold")]), Space(), Str("word.")
    ]
    assert markdown == "A **bold** word."
    assert plain_text == "A bold word."


def test_bold_letter():
    notion_data = mock_rich_text_array([('A ', []), ('b', ['bold']), ('old word.', [])])
    pandoc_ast, markdown, plain_text = process_rich_text_array(notion_data)
    assert pandoc_ast == [
        Str("A"), Space(), Strong([Str("b")]), Str("old"), Space(), Str("word.")
    ]
    assert markdown == "A **b**old word."
    assert plain_text == "A bold word."


def test_bold_spaces():
    notion_data = mock_rich_text_array([('A', []), (' bold ', ['bold']), ('word.', [])])
    pandoc_ast, markdown, plain_text = process_rich_text_array(notion_data)
    assert pandoc_ast == [
        Str("A"), Space(), Strong([Str("bold")]), Space(), Str("word.")
    ]
    assert markdown == "A **bold** word."
    assert plain_text == "A bold word."


def test_italic_word():
    notion_data = mock_rich_text_array([('An ', []), ('italic', ['italic']), (' word.', [])])
    pandoc_ast, markdown, _ = process_rich_text_array(notion_data)
    assert pandoc_ast == [
        Str("An"), Space(), Emph([Str("italic")]), Space(), Str("word.")
    ]
    assert markdown == "An *italic* word."


def test_italic_letter():
    notion_data = mock_rich_text_array([('An ', []), ('i', ['italic']), ('talic word.', [])])
    pandoc_ast, markdown, _ = process_rich_text_array(notion_data)
    assert pandoc_ast == [Str("An"), Space(), Emph([Str("i")]), Str("talic"), Space(), Str("word.")]
    assert markdown == "An *i*talic word."


def test_bold_italic_word():
    notion_data = mock_rich_text_array([
        ('A ', []),
        ('bold-italic', ['bold', 'italic']),
        (' word.', []),
    ])
    pandoc_ast, markdown, plain_text = process_rich_text_array(notion_data)
    assert pandoc_ast == [
        Str('A'),
        Space(),
        Emph([Strong([Str('bold-italic')])]),
        Space(),
        Str('word.'),
    ]
    assert markdown == "A ***bold-italic*** word."
    assert plain_text == "A bold-italic word."


def test_bold_space():
    notion_data = mock_rich_text_array([
        (' ', ['bold']),
    ])
    pandoc_ast, _, _ = process_rich_text_array(notion_data)
    assert pandoc_ast == [Space()]


def test_italic_spaces():
    notion_data = mock_rich_text_array([('An', []), (' italic ', ['italic']), ('word.', [])])
    pandoc_ast, markdown, plain_text = process_rich_text_array(notion_data)
    assert pandoc_ast == [Str('An'), Space(), Emph([Str('italic')]), Space(), Str('word.')]
    assert markdown == "An *italic* word."
    assert plain_text == "An italic word."


def test_strikeout_word():
    notion_data = mock_rich_text_array([('A ', []), ('deleted', ['strikethrough']), (' word.', [])])
    pandoc_ast, markdown, plain_text = process_rich_text_array(notion_data)
    assert pandoc_ast == [Str("A"), Space(), Strikeout([Str("deleted")]), Space(), Str("word.")]
    assert markdown == "A ~~deleted~~ word."
    assert plain_text == "A deleted word."


def test_strikeout_spaces():
    notion_data = mock_rich_text_array([('A', []), (' deleted ', ['strikethrough']), ('word.', [])])
    pandoc_ast, markdown, _ = process_rich_text_array(notion_data)
    assert pandoc_ast == [Str("A"), Space(), Strikeout([Str("deleted")]), Space(), Str("word.")]
    assert markdown == "A ~~deleted~~ word."


def test_blended_annotated_spaces():
    notion_data = mock_rich_text_array([
        ('this ', ['bold']),
        ('is ', ['bold', 'italic']),
        ('a', ['italic']),
        (' test', ['strikethrough']),
        (' did', ['bold', 'underline', 'code']),
        (' i pass', ['underline', 'code']),
        ('?', [])
    ])
    pandoc_ast, _, _ = process_rich_text_array(notion_data)
    assert pandoc_ast == [
        Strong([Str('this')]),
        Space(),
        Emph([Strong([Str('is')])]),
        Space(),
        Emph([Str('a')]),
        Space(),
        Strikeout([Str('test')]),
        Underline([Strong([Code(('', [], []), ' did')])]),
        Underline([Code(('', [], []), ' i pass')]),
        Str('?')
    ]
    # TODO: add assertion for markdown


def test_equation_inline():
    lhs = "{\\displaystyle i\\hbar {\\frac {d}{dt}}\\vert "
    rhs = "\\Psi (t)\\rangle={\\hat {H}}\\vert \\Psi (t)\\rangle}"
    example_equation = f"{lhs}{rhs}"

    notion_data = [
        mock_rich_text('The Schr??dinger Equation ('),
        {
            'type': 'equation',
            'equation': {'expression': example_equation},
            'annotations': mock_annotations(),
            'plain_text': example_equation,
            'href': None,
        },
        mock_rich_text(') is a very useful one indeed'),
    ]

    pandoc_ast, markdown, _ = process_rich_text_array(notion_data)
    assert pandoc_ast == [
        Str('The'), Space(), Str('Schr??dinger'), Space(), Str('Equation'), Space(), Str('('),
        Math(InlineMath(), example_equation), Str(')'), Space(),
        Str('is'), Space(), Str('a'), Space(), Str('very'), Space(),
        Str('useful'), Space(), Str('one'), Space(), Str('indeed'),
    ]
    md1 = "The Schr??dinger Equation (${\\displaystyle i\\hbar "
    md2 = "{\\frac {d}{dt}}\\vert \\Psi (t)\\rangle={\\hat "
    md3 = "{H}}\\vert \\Psi (t)\\rangle}$) is a very useful one indeed"
    assert markdown == f"{md1}{md2}{md3}"


def test_code_inline():
    notion_data = mock_rich_text_array([('A ', []), ('code', ['code']), (' word.', [])])
    pandoc_ast, markdown, plain_text = process_rich_text_array(notion_data)
    assert pandoc_ast == [Str("A"), Space(), Code(("", [], []), "code"), Space(), Str("word.")]
    assert markdown == "A `code` word."
    assert plain_text == "A code word."


def test_link_inline():
    notion_data = [
        mock_rich_text("This is a "),
        mock_rich_text("link", ["bold"], href="https://example.com"),
        mock_rich_text("."),
    ]
    pandoc_ast, markdown, plain_text = process_rich_text_array(notion_data)
    assert pandoc_ast == [
        Str('This'), Space(), Str('is'), Space(), Str('a'), Space(),
        Link(('', [], []), [Strong([Str('link')])], ('https://example.com', '')),
        Str('.'),
    ]
    assert markdown == 'This is a [**link**](https://example.com).'
    assert plain_text == 'This is a link.'

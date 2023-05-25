from pandoc.types import (
    Str, Space, Strong, Emph, Strikeout, Code, Link, Math, InlineMath,
    Underline
)

from n2y.notion import Client
from n2y.rich_text import RichTextArray, MentionRichText
from n2y.mentions import PageMention
from n2y.notion_mocks import mock_rich_text_array, mock_annotations, mock_rich_text, mock_id


def process_rich_text_array(notion_data):
    client = Client('')
    rich_text_array = client.wrap_notion_rich_text_array(notion_data)
    pandoc_ast = rich_text_array.to_pandoc()
    markdown = rich_text_array.to_value('markdown')
    plain_text = rich_text_array.to_plain_text()
    return pandoc_ast, markdown, plain_text


def test_bold_word():
    notion_data = mock_rich_text_array([('A ', []), ('bold', ['bold']), (' word.', [])])
    pandoc_ast, markdown, plain_text = process_rich_text_array(notion_data)
    assert pandoc_ast == [
        Str("A"), Space(), Strong([Str("bold")]), Space(), Str("word.")
    ]
    assert markdown == "A **bold** word.\n"
    assert plain_text == "A bold word."


def test_bold_letter():
    notion_data = mock_rich_text_array([('A ', []), ('b', ['bold']), ('old word.', [])])
    pandoc_ast, markdown, plain_text = process_rich_text_array(notion_data)
    assert pandoc_ast == [
        Str("A"), Space(), Strong([Str("b")]), Str("old"), Space(), Str("word.")
    ]
    assert markdown == "A **b**old word.\n"
    assert plain_text == "A bold word."


def test_bold_spaces():
    notion_data = mock_rich_text_array([('A', []), (' bold ', ['bold']), ('word.', [])])
    pandoc_ast, markdown, plain_text = process_rich_text_array(notion_data)
    assert pandoc_ast == [
        Str("A"), Space(), Strong([Str("bold")]), Space(), Str("word.")
    ]
    assert markdown == "A **bold** word.\n"
    assert plain_text == "A bold word."


def test_italic_word():
    notion_data = mock_rich_text_array([('An ', []), ('italic', ['italic']), (' word.', [])])
    pandoc_ast, markdown, _ = process_rich_text_array(notion_data)
    assert pandoc_ast == [
        Str("An"), Space(), Emph([Str("italic")]), Space(), Str("word.")
    ]
    assert markdown == "An *italic* word.\n"


def test_italic_letter():
    notion_data = mock_rich_text_array([('An ', []), ('i', ['italic']), ('talic word.', [])])
    pandoc_ast, markdown, _ = process_rich_text_array(notion_data)
    assert pandoc_ast == [Str("An"), Space(), Emph([Str("i")]), Str("talic"), Space(), Str("word.")]
    assert markdown == "An *i*talic word.\n"


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
    assert markdown == "A ***bold-italic*** word.\n"
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
    assert markdown == "An *italic* word.\n"
    assert plain_text == "An italic word."


def test_strikeout_word():
    notion_data = mock_rich_text_array([('A ', []), ('deleted', ['strikethrough']), (' word.', [])])
    pandoc_ast, markdown, plain_text = process_rich_text_array(notion_data)
    assert pandoc_ast == [Str("A"), Space(), Strikeout([Str("deleted")]), Space(), Str("word.")]
    assert markdown == "A ~~deleted~~ word.\n"
    assert plain_text == "A deleted word."


def test_strikeout_spaces():
    notion_data = mock_rich_text_array([('A', []), (' deleted ', ['strikethrough']), ('word.', [])])
    pandoc_ast, markdown, _ = process_rich_text_array(notion_data)
    assert pandoc_ast == [Str("A"), Space(), Strikeout([Str("deleted")]), Space(), Str("word.")]
    assert markdown == "A ~~deleted~~ word.\n"


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
    pandoc_ast, markdown, _ = process_rich_text_array(notion_data)
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
    assert markdown == (
        '**this** ***is*** *a*\n~~test~~[**` did`*'
        '*]{.underline}[` i pass`]{.underline}?\n'
    )


def test_equation_inline():
    lhs = "{\\displaystyle i\\hbar {\\frac {d}{dt}}\\vert "
    rhs = "\\Psi (t)\\rangle={\\hat {H}}\\vert \\Psi (t)\\rangle}"
    example_equation = f"{lhs}{rhs}"

    notion_data = [
        mock_rich_text('The Schrödinger Equation ('),
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
        Str('The'), Space(), Str('Schrödinger'), Space(), Str('Equation'), Space(), Str('('),
        Math(InlineMath(), example_equation), Str(')'), Space(),
        Str('is'), Space(), Str('a'), Space(), Str('very'), Space(),
        Str('useful'), Space(), Str('one'), Space(), Str('indeed'),
    ]
    assert markdown == (
        'The Schrödinger Equation\n(${\\displaystyle '
        'i\\hbar {\\frac {d}{dt}}\\vert \\Psi (t)\\'
        'rangle={\\hat {H}}\\vert \\Psi (t)\\rangle}$)\nis'
        ' a very useful one indeed\n'
    )


def test_code_inline():
    notion_data = mock_rich_text_array([('A ', []), ('code', ['code']), (' word.', [])])
    pandoc_ast, markdown, plain_text = process_rich_text_array(notion_data)
    assert pandoc_ast == [Str("A"), Space(), Code(("", [], []), "code"), Space(), Str("word.")]
    assert markdown == "A `code` word.\n"
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
    assert markdown == 'This is a [**link**](https://example.com).\n'
    assert plain_text == 'This is a link.'


def test_prepend():
    client = Client('')
    plain_data = mock_rich_text_array('plain text')
    mention_data = {'type': 'page', 'page': {'id': mock_id()}}
    mention_text = 'Test Page'
    mention_block = PageMention(client, mention_data, mention_text)
    mention_rich_text = MentionRichText(
        client,
        mock_rich_text(
            mention_text,
            None,
            None,
            mention_data
        ),
        None,
        mention_block
    )
    equation_text = 'e=mc^2'
    equation_data = mock_rich_text_array([[
        equation_text,
        None,
        None,
        None,
        None,
        {'expression': equation_text}
    ]])
    plain = RichTextArray(client, plain_data)
    mention = RichTextArray(client, [])
    equation = RichTextArray(client, equation_data)
    mention.items.append(mention_rich_text)
    assert plain.to_pandoc() == [Str('plain'), Space(), Str('text')]
    assert mention.to_pandoc() == [Str('Test'), Space(), Str('Page')]
    assert equation.to_pandoc() == [Math(InlineMath(), equation_text)]

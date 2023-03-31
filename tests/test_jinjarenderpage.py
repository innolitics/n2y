from jinja2 import TemplateSyntaxError
from pytest import raises

from n2y.notion import Client
from n2y.blocks import ChildPageBlock
from n2y.utils import pandoc_ast_to_markdown
from n2y.plugins.jinjarenderpage import render_from_string, join_to, fuzzy_in, JinjaFencedCodeBlock, JinjaRenderPage
from n2y.notion_mocks import mock_page, mock_rich_text_array, mock_block


def test_join_to_basic():
    foreign_keys = ['1', '3']
    table = [
        {'id': '1', 'data': 'a'},
        {'id': '2', 'data': 'b'},
    ]
    assert join_to(foreign_keys, table) == [{'id': '1', 'data': 'a'}, None]
    assert join_to(foreign_keys, table, 'data') == [None, None]


def test_fuzzy_in_quotes():
    assert fuzzy_in('a"b', 'a\u201cb')
    assert fuzzy_in('a\u201cb', 'a"b')
    assert fuzzy_in('"', '\u201d')
    assert fuzzy_in('\u201d', '"')


def test_fuzzy_in_ellipse():
    assert fuzzy_in('a\u2026b', 'a...b')
    assert fuzzy_in('a...b', 'a\u2026b')
    assert fuzzy_in('\u2026', '...')
    assert fuzzy_in('...', '\u2026')


def test_fuzzy_in_em_dash():
    assert fuzzy_in('a\u2014b', 'a---b')
    assert fuzzy_in('a---b', 'a\u2014b')
    assert fuzzy_in('\u2014', '---')
    assert fuzzy_in('---', '\u2014')


def test_fuzzy_in_en_dash():
    assert fuzzy_in('a\u2013b', 'a--b')
    assert fuzzy_in('a--b', 'a\u2013b')
    assert fuzzy_in('\u2013', '--')
    assert fuzzy_in('--', '\u2013')


def test_render_no_filtering():
    input_string = "apple\nbanana\ncherry\n"
    expected_result = input_string
    actual_result = render_from_string(input_string)
    assert actual_result == expected_result


def test_undefined():
    with raises(TemplateSyntaxError):
        input_string = "{% huhwhat 'hotel', 'california' %}"
        render_from_string(input_string)


def process_jinja_block(client, caption, jinja_code):
    page_notion_data = mock_page()
    page = JinjaRenderPage(client, page_notion_data)

    page_block_notion_data = mock_block('child_page', {'title': "Mock Page"})
    page_block = ChildPageBlock(client, page_block_notion_data, page, False)

    page._block = page_block

    code_block_notion_data = mock_block('code', {
        'language': 'plain text',
        'caption': caption,
        'rich_text': mock_rich_text_array(jinja_code)
    })
    code_block = JinjaFencedCodeBlock(client, code_block_notion_data, page, False)
    page.block.children = [code_block]
    return page


def test_jinja_syntax_err():
    client = Client('', exports=[])
    caption = mock_rich_text_array('{jinja=gfm}')
    jinja_code = "{% huhwhat 'hotel', 'california' %}"
    page = process_jinja_block(client, caption, jinja_code)
    with raises(TemplateSyntaxError):
        page.to_pandoc()


def test_jinja_render():
    client = Client('', exports=[])
    caption = mock_rich_text_array('{jinja=gfm}')
    jinja_code = "{% for v in ['a', 'b'] %}{{v}}{% endfor %}"
    page = process_jinja_block(client, caption, jinja_code)
    pandoc_ast = page.to_pandoc()
    markdown = pandoc_ast_to_markdown(pandoc_ast)
    assert markdown == "ab\n"


def test_jinja_render_with_second_pass():
    pass
    # TODO fill this in


def test_jinja_render_with_database():
    pass
    # TODO fill this in

from jinja2 import TemplateSyntaxError
from pytest import raises

from n2y.notion import Client
from n2y.blocks import ChildPageBlock
from n2y.plugins.rawcodeblocks import RawFencedCodeBlock
from tests.utils import render_from_string, invert_dependencies
from n2y.plugins.jinjarenderpage import join_to, JinjaRenderPage
from n2y.notion_mocks import mock_page, mock_rich_text_array, mock_block, mock_id, mock_database


def test_invert_dependencies_single():
    objects = [
        {'id': 'a', 'dependencies': ['r-1', 'r-2']}
    ]
    actual = invert_dependencies(objects, 'id', 'dependencies')
    expected = [('r-1', {'a'}), ('r-2', {'a'})]
    assert actual == expected


def test_invert_dependencies_multiple():
    objects = [
        {'id': 'a', 'dependencies': ['r-1', 'r-2', 'r-3-2']},
        {'id': 'b', 'dependencies': ['r-1', 'r-2', 'r-3-1']},
    ]
    actual = invert_dependencies(objects, 'id', 'dependencies')
    expected = [
        ('r-1', {'a', 'b'}),
        ('r-2', {'a', 'b'}),
        ('r-3-1', {'b'}),
        ('r-3-2', {'a'}),
    ]
    assert actual == expected


def test_join_to_basic():
    foreign_keys = ['1', '3']
    table = [
        {'id': '1', 'data': 'a'},
        {'id': '2', 'data': 'b'},
    ]
    assert join_to(foreign_keys, table) == [{'id': '1', 'data': 'a'}, None]
    assert join_to(foreign_keys, table, 'data') == [None, None]


def test_render_no_filtering():
    input_string = "apple\nbanana\ncherry\n"
    expected_result = input_string
    actual_result = render_from_string(input_string)
    assert actual_result == expected_result


def test_undefined():
    with raises(TemplateSyntaxError):
        input_string = "{% huhwhat 'hotel', 'california' %}"
        render_from_string(input_string)

def test_jinja_syntax_err():
    client = Client('', exports=[])
    database_notion_data = mock_database()
    database_id = database_notion_data['id']
    database_block = client._wrap_notion_database(database_notion_data)
    client.databases_cache[database_id] = database_block
    page_notion_data = mock_page()
    page_notion_data['parent'] = {'type': 'database_id', 'database_id': database_id}
    page_block = JinjaRenderPage(client, page_notion_data)
    page_notion_data['has_children'] = False
    page_notion_data['type'] = 'child_page'
    page_notion_data['child_page'] = {'title': "Mock Page"}
    child_page = ChildPageBlock(client, page_notion_data, page_block, False)
    page_block._block = child_page
    code_notion_type_data = {
        'language': 'plain text',
        'caption': mock_rich_text_array('{=gfm}'),
        'rich_text': mock_rich_text_array("{% huhwhat 'hotel', 'california' %}")
    }
    code_notion_data = mock_block('code', code_notion_type_data)
    code_block = RawFencedCodeBlock(client, code_notion_data, page_block, False)
    page_block.block.children = [code_block]
    with raises(TemplateSyntaxError):
        page_block.to_pandoc()
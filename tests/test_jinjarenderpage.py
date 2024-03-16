from unittest.mock import PropertyMock, patch

from jinja2 import TemplateSyntaxError
from pytest import raises

from n2y.blocks import ChildPageBlock
from n2y.notion import Client
from n2y.notion_mocks import (
    mock_block,
    mock_database,
    mock_database_mention,
    mock_page,
    mock_rich_text,
    mock_rich_text_array,
    mock_user,
)
from n2y.page import Page
from n2y.plugins.jinjarenderpage import (
    JinjaFencedCodeBlock,
    JinjaRenderPage,
    fuzzy_find_in,
    join_to,
    list_matches,
    render_from_string,
)
from n2y.user import User
from n2y.utils import pandoc_ast_to_markdown, pandoc_write_or_log_errors

format_def = "{jinja=gfm}"
spaced_format_def = "{jinja=gfm} "


def test_join_to_basic():
    foreign_keys = ["1", "3"]
    table = [
        {"notion_id": "1", "data": "a"},
        {"notion_id": "2", "data": "b"},
    ]
    assert join_to(foreign_keys, table) == [{"notion_id": "1", "data": "a"}, None]
    assert join_to(foreign_keys, table, "data") == [None, None]


def test_fuzzy_find_in():
    dict_list = [
        {"id": "1", "data": "a"},
        {"id": "2", "data": "bc"},
        {"id": "3", "data": "def"},
    ]
    reversed_dict_list = [
        {"id": "3", "data": "def"},
        {"id": "2", "data": "bc"},
        {"id": "1", "data": "a"},
    ]
    catch_all_string = "a bc def"
    assert fuzzy_find_in(dict_list, "a", "data") == [{"id": "1", "data": "a"}]
    assert fuzzy_find_in(dict_list, catch_all_string, "data") == reversed_dict_list
    assert fuzzy_find_in(dict_list, catch_all_string, "data", False) == reversed_dict_list
    assert fuzzy_find_in(dict_list, catch_all_string, "data", False, False) == dict_list
    assert fuzzy_find_in(dict_list, catch_all_string, "data", True, False) == dict_list


def test_render_no_filtering():
    input_string = "apple\nbanana\ncherry\n"
    expected_result = input_string
    actual_result = render_from_string(input_string)
    assert actual_result == expected_result


def test_undefined():
    with raises(TemplateSyntaxError):
        input_string = "{% huhwhat 'hotel', 'california' %}"
        render_from_string(input_string)


@patch("n2y.notion.Client.wrap_notion_user")
def process_jinja_block(client, caption, jinja_code, wrap_notion_user):
    wrap_notion_user.return_value = User(client, mock_user())
    page_notion_data = mock_page()
    page = JinjaRenderPage(client, page_notion_data)

    page_block_notion_data = mock_block("child_page", {"title": "Mock Page"})
    page_block = ChildPageBlock(client, page_block_notion_data, page, False)

    page._block = page_block

    code_block_notion_data = mock_block(
        "code",
        {
            "language": "plain text",
            "caption": caption,
            "rich_text": mock_rich_text_array(jinja_code),
        },
    )
    code_block = JinjaFencedCodeBlock(client, code_block_notion_data, page, False)
    page.block.children = [code_block]
    return page


def test_jinja_syntax_err():
    client = Client("")
    caption = mock_rich_text_array(format_def)
    jinja_code = "{% huhwhat 'hotel', 'california' %}"
    page = process_jinja_block(client, caption, jinja_code)
    pandoc_ast = page.to_pandoc()
    markdown = pandoc_ast_to_markdown(pandoc_ast, client.logger)
    assert "syntax error" in markdown
    assert "Encountered unknown tag 'huhwhat'" in markdown


def test_jinja_render_gfm():
    client = Client("")
    caption = mock_rich_text_array(format_def)
    jinja_code = "{% for v in ['a', 'b'] %}{{v}}{% endfor %}"
    page = process_jinja_block(client, caption, jinja_code)
    pandoc_ast = page.to_pandoc()
    markdown = pandoc_ast_to_markdown(pandoc_ast, client.logger)
    assert markdown == "ab\n"


def test_jinja_render_gfm_with_second_pass():
    client = Client("")
    caption = mock_rich_text_array(format_def)
    jinja_code = "a{% for v in first_pass_output.lines %}{{v}}{% endfor %}"
    page = process_jinja_block(client, caption, jinja_code)
    page_block = page.block
    with patch.object(Page, "block", new_callable=PropertyMock) as mock_block:
        mock_block.return_value = page_block
        pandoc_ast = page.to_pandoc()
    markdown = pandoc_ast_to_markdown(pandoc_ast, client.logger)
    assert markdown == "aa\n"


def test_jinja_render_html():
    client = Client("")
    caption = mock_rich_text_array("{jinja=html}")
    jinja_code = (
        "<table>"
        "<tr><th>Name</th></tr>"
        "{% for v in ['a', 'b'] %}<tr><td>{{v}}</td></tr>{% endfor %}"
        "</table>"
    )
    page = process_jinja_block(client, caption, jinja_code)
    pandoc_ast = page.to_pandoc()
    markdown = pandoc_ast_to_markdown(pandoc_ast, client.logger)
    assert markdown == "  Name\n  ------\n  a\n  b\n"


@patch("n2y.notion.Client.wrap_notion_user")
def test_jinja_render_with_database(wrap_notion_user):
    client = Client("")
    wrap_notion_user.return_value = User(client, mock_user())
    database_notion_data = mock_database(title="My DB")
    mention_notion_data = mock_database_mention(database_notion_data["id"])
    database_pages_notion_data = [mock_page(title="a"), mock_page(title="b")]
    caption = [
        mock_rich_text(spaced_format_def),
        mock_rich_text("My DB", mention=mention_notion_data),
    ]
    jinja_code = "{% for v in databases['My DB'] %}{{v.title}}{% endfor %}"

    with patch.object(Client, "get_notion_database") as mock_get_notion_database:
        with patch.object(
            Client, "get_database_notion_pages"
        ) as mock_get_database_notion_pages:
            mock_get_notion_database.return_value = database_notion_data
            mock_get_database_notion_pages.return_value = database_pages_notion_data
            page = process_jinja_block(client, caption, jinja_code)
            pandoc_ast = page.to_pandoc()

    markdown = pandoc_ast_to_markdown(pandoc_ast, client.logger)
    assert markdown == "ab\n"


@patch("n2y.notion.Client.wrap_notion_user")
def test_jinja_render_with_missing_database(wrap_notion_user):
    client = Client("")
    wrap_notion_user.return_value = User(client, mock_user())
    database_notion_data = mock_database(title="My DB")
    mention_notion_data = mock_database_mention(database_notion_data["id"])
    database_pages_notion_data = [mock_page(title="a"), mock_page(title="b")]
    caption = [
        mock_rich_text(spaced_format_def),
        mock_rich_text("My DB", mention=mention_notion_data),
    ]
    jinja_code = "{{ databases['MISSING'] }}"

    with patch.object(Client, "get_notion_database") as mock_get_notion_database:
        with patch.object(
            Client, "get_database_notion_pages"
        ) as mock_get_database_notion_pages:
            mock_get_notion_database.return_value = database_notion_data
            mock_get_database_notion_pages.return_value = database_pages_notion_data
            page = process_jinja_block(client, caption, jinja_code)
            pandoc_ast = page.to_pandoc()

    markdown = pandoc_ast_to_markdown(pandoc_ast, client.logger)
    assert 'You attempted to access the "MISSING" database' in markdown
    assert 'the only available database is "My DB".' in markdown


@patch("n2y.notion.Client.wrap_notion_user")
def test_jinja_render_with_incorrect_db_property(wrap_notion_user):
    client = Client("")
    wrap_notion_user.return_value = User(client, mock_user())
    database_notion_data = mock_database(title="My DB")
    mention_notion_data = mock_database_mention(database_notion_data["id"])
    database_pages_notion_data = [mock_page(title="a"), mock_page(title="b")]
    caption = [
        mock_rich_text(spaced_format_def),
        mock_rich_text("My DB", mention=mention_notion_data),
    ]
    jinja_code = "{{ databases[0][0].Foo }}"

    with patch.object(Client, "get_notion_database") as mock_get_notion_database:
        with patch.object(
            Client, "get_database_notion_pages"
        ) as mock_get_database_notion_pages:
            mock_get_notion_database.return_value = database_notion_data
            mock_get_database_notion_pages.return_value = database_pages_notion_data
            page = process_jinja_block(client, caption, jinja_code)
            pandoc_ast = page.to_pandoc()

    markdown = pandoc_ast_to_markdown(pandoc_ast, client.logger)
    assert (
        'You attempted to access the "Foo" property of a database item on line 1'
        in markdown
    )
    assert (
        'the available properties are "title", "notion_id", and "notion_url".' in markdown
    )


@patch("n2y.notion.Client.wrap_notion_user")
def test_jinja_render_with_missing_page_property(wrap_notion_user):
    client = Client("")
    wrap_notion_user.return_value = User(client, mock_user())
    database_notion_data = mock_database(title="My DB")
    mention_notion_data = mock_database_mention(database_notion_data["id"])
    database_pages_notion_data = [mock_page(title="a"), mock_page(title="b")]
    caption = [
        mock_rich_text(spaced_format_def),
        mock_rich_text("My DB", mention=mention_notion_data),
    ]
    jinja_code = "{{ page['MISSING'] }}"

    with patch.object(Client, "get_notion_database") as mock_get_notion_database:
        with patch.object(
            Client, "get_database_notion_pages"
        ) as mock_get_database_notion_pages:
            mock_get_notion_database.return_value = database_notion_data
            mock_get_database_notion_pages.return_value = database_pages_notion_data
            page = process_jinja_block(client, caption, jinja_code)
            pandoc_ast = page.to_pandoc()

    markdown = pandoc_ast_to_markdown(pandoc_ast, client.logger)
    assert 'You attempted to access the "MISSING" property' in markdown
    assert 'the only available property is "title".' in markdown


@patch("n2y.notion.Client.wrap_notion_user")
def test_jinja_render_with_filter_error(wrap_notion_user):
    client = Client("")
    wrap_notion_user.return_value = User(client, mock_user())
    database_notion_data = mock_database(title="My DB")
    mention_notion_data = mock_database_mention(database_notion_data["id"])
    database_pages_notion_data = [mock_page(title="a"), mock_page(title="b")]
    caption = [
        mock_rich_text(spaced_format_def),
        mock_rich_text("My DB", mention=mention_notion_data),
    ]
    jinja_code = "{{ databases[0][0].title|round }}"

    with patch.object(Client, "get_notion_database") as mock_get_notion_database:
        with patch.object(
            Client, "get_database_notion_pages"
        ) as mock_get_database_notion_pages:
            mock_get_notion_database.return_value = database_notion_data
            mock_get_database_notion_pages.return_value = database_pages_notion_data
            page = process_jinja_block(client, caption, jinja_code)
            pandoc_ast = page.to_pandoc()

    markdown = pandoc_ast_to_markdown(pandoc_ast, client.logger)
    assert 'Recieved the message "type str doesn\'t define __round__ method"' in markdown
    assert 'The Jinja filter "round" raised this error' in markdown
    assert 'argument(s): {\n\t"args": (\'a\',),\n\t"kwargs": {}\n}' in markdown


def test_jinja_render_plain():
    client = Client("")
    caption = mock_rich_text_array("{jinja=plain}")
    jinja_code = "# <h1> asdf23"
    page = process_jinja_block(client, caption, jinja_code)
    pandoc_ast = page.to_pandoc()
    text = pandoc_write_or_log_errors(pandoc_ast, "plain", [], client.logger)
    assert text == "# <h1> asdf23\n"


def test_list_matches_special_characters():
    text = "somthing (id_num) [category] note* $tag (?!question)"
    string = (
        "fdsfds dwefwe 342t45lsfd fdds f34244 dgd somthing "
        "(id_num) [category] note* $tag (?!question) dsfsa "
        "sdfasdfsad"
    )
    assert len(list_matches(text, string)) == 1


def test_list_matches_no_space_fail():
    text = "somthing (id_num) [category] note* $tag (?!question)"
    string = (
        "fdsfds dwefwe 342t45lsfd fdds f34244 dgd sfdasomthing "
        "(id_num) [category] note* $tag (?!question) dsfsa "
        "sdfasdfsad"
    )
    assert len(list_matches(text, string)) == 0

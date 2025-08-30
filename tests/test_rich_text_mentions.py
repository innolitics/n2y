from pandoc.types import (
    Link,
    Str,
)
from n2y.notion import Client
from n2y.notion_mocks import mock_rich_text_array
from tests.utils import newline_lf


def process_rich_text_array(notion_data):
    client = Client("")
    rich_text_array = client.wrap_notion_rich_text_array(notion_data)
    pandoc_ast = rich_text_array.to_pandoc()
    markdown = rich_text_array.to_value("markdown", [])
    plain_text = rich_text_array.to_plain_text()
    return pandoc_ast, markdown, plain_text


def test_link_mention():
    link_text = "Example Site"
    link_url = "https://example.com"

    expected_ast = [
        Link(('', [], []), [Str(link_text)], (link_url, '')),
    ]
    expected_markdown = f"[{link_text}]({link_url})\n"
    expected_plain = link_text

    # old shape (url)
    link_mention_data_old = {
        "type": "link_mention",
        "link_mention": {"url": link_url},
    }
    notion_data_old = mock_rich_text_array([(link_text, [], None, link_mention_data_old)])
    pandoc_ast, markdown, plain_text = process_rich_text_array(notion_data_old)

    assert pandoc_ast == expected_ast
    assert newline_lf(markdown) == expected_markdown
    assert plain_text == expected_plain

    # new shape (href + title + description)
    link_mention_data_new = {
        "type": "link_mention",
        "link_mention": {
            "href": link_url,
            "title": link_text,
            "description": "A description from Notion metadata",
        },
    }
    notion_data_new = mock_rich_text_array([(link_text, [], None, link_mention_data_new)])
    pandoc_ast, markdown, plain_text = process_rich_text_array(notion_data_new)

    assert pandoc_ast == expected_ast
    assert newline_lf(markdown) == expected_markdown
    assert plain_text == expected_plain

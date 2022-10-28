from n2y.notion import Client
from n2y.notion_mocks import mock_block, mock_rich_text
from n2y.utils import id_from_share_link
from tests.utils import NOTION_ACCESS_TOKEN


def test_create_and_delete_blocks():
    url = "cfa8ff07bba244c8b967c9b6a7a954c1"
    client = Client(NOTION_ACCESS_TOKEN, plugins=None)
    object_id = id_from_share_link(url)
    page = client.get_page_or_database(object_id)
    notion_block = mock_block(
        "heading_2",
        {
            "color": "default",
            "rich_text": [mock_rich_text("m")],
        },
        has_children=True
    )
    del notion_block["url"]
    creation_response = client.append_block_children(page.notion_id, [notion_block])
    new_block_id = creation_response[0]['id']
    deletion_response = client.delete_block(new_block_id)
    assert creation_response
    assert deletion_response

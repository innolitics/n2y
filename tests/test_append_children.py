from n2y.notion import Client
from n2y.notion_mocks import mock_block, mock_database, mock_page, mock_rich_text
from tests.utils import NOTION_ACCESS_TOKEN


def test_append_and_delete_blocks():
    client = Client(NOTION_ACCESS_TOKEN, plugins=None)
    object_id = "c9e17a34da6a4b3295f82a1ad05bc3d8"
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
    creation_response = client.append_child_notion_blocks(page.notion_id, [notion_block])
    new_block = creation_response[0]
    deletion_response = client.delete_notion_block(new_block)
    assert creation_response
    assert deletion_response


def test_append_child_page_or_database():
    client = Client(NOTION_ACCESS_TOKEN, plugins=None)
    object_id = "c9e17a34da6a4b3295f82a1ad05bc3d8"
    page = client.get_page_or_database(object_id)
    parent = {'type': 'page_id', 'page_id': page.notion_id}
    child_database = mock_database('Child_Database')
    child_page = mock_page('Child_Page')
    child_database['parent'] = parent
    child_page['parent'] = parent
    del child_database['url']
    del child_page['url']
    creation_response = client.append_child_notion_blocks(object_id, [child_database, child_page])
    assert creation_response
    for child in creation_response:
        deletion_response = client.delete_notion_block(child)
        assert deletion_response

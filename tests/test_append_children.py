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
    destination_id = "c9e17a34da6a4b3295f82a1ad05bc3d8"
    original_id = "0b25a11e78b348c993b4dcf869f25a91"
    original = client.get_page_or_database(original_id)
    child_database = original.block.children[-1].notion_data
    child_page = original.block.children[-2].notion_data
    print(child_page)
    print(child_database)
    creation_response = client.append_child_notion_blocks(destination_id, [child_database, child_page])
    assert creation_response
    for child in creation_response:
        deletion_response = client.delete_notion_block(child)
        assert deletion_response

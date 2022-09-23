from n2y.notion import Client
from n2y.notion_mocks import mock_block, mock_rich_text
from n2y.utils import id_from_share_link


def test_create_and_delete_blocks():
    url = "https://www.notion.so/innolitics/Test-Page-46bc615bed5a479e8390d9373279426f"
    access_token = "secret_aBbNlu5xsTtBNarAmuPYliS6pSCMpNaIJkcsz5eFuZn"
    client = Client(access_token, plugins=None)
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
    new_block_id = creation_response['results'][0]['id']
    deletion_response = client.delete_block(new_block_id)
    assert creation_response
    assert deletion_response
from unittest import mock
from n2y.notion import Client
from tests.test_blocks import generate_block


def generate_block(notion_block, plugins=None):
    with mock.patch.object(Client, "get_notion_block") as mock_get_notion_block:
        mock_get_notion_block.return_value = notion_block
        client = Client("", plugins=plugins)
        page = None
        return client.get_block("unusedid", page)


def test_create_and_delete_blocks():
    client = Client("", plugins=None)
    client.
    print(generate_block())
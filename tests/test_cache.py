from n2y.cache import Cache
from n2y.notion_mocks import mock_block, mock_rich_text, mock_paragraph_block
from n2y import notion
import os
from unittest import mock

from n2y.notion import Client

from tests.test_blocks import generate_block




client = notion.Client(os.environ.get('NOTION_ACCESS_TOKEN'))


def test_cache_child_notion_blocks():

    notion_block = mock_block("paragraph", {"rich_text": [mock_rich_text("parent")]}, True)
    
    child_notion_blocks = [mock_paragraph_block([("child", [])])]

    with mock.patch.object(
        Client, "get_child_notion_blocks"
    ) as mock_get_child_notion_blocks:
        mock_get_child_notion_blocks.return_value = child_notion_blocks
        n2y_block = generate_block(notion_block)

        #TODO: Check data structures here.
        
        n2y_block.last_edited_time = 0

    client.cache.cache_child_notion_blocks(parent.id, parent.content, children.child_notion_blocks, parent.last_edited_time)
 
    cached_block = client.cache.get_child_notion_blocks(parent.id)

    assert cached_block  == parent.content


def test_cache_block():

    block = mock_block("paragraph", {"rich_text": [mock_rich_text("Lorem ipsum")]}, False)

    client.cache.cache_notion_block(block["id"], block, block["last_edited_time"])

    cached_block, timestamp = client.cache.get_notion_block(block["id"])

    # TODO: Should be storing the whole block object, not just its contents, to the cache.
    assert cached_block == block

test_cache_block()
test_cache_child_notion_blocks()
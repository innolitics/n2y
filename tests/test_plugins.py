import pytest

from n2y.blocks import ParagraphBlock
from n2y.notion import Client
from n2y.page import Page
from n2y.errors import PluginError, UseNextClass
from tests.notion_mocks import mock_paragraph_block


def test_load_plugin_invalid_notion_object():
    client = Client('')
    with pytest.raises(PluginError) as err:
        client.load_plugin({"puppy": str})
    assert "puppy" in str(err)


def test_load_plugin_invalid_object_type():
    client = Client('')
    with pytest.raises(PluginError) as err:
        client.load_plugin({"blocks": {"puppy": str}})
    assert "block" in str(err)
    assert "puppy" in str(err)


def test_load_plugin_valid_page():
    client = Client('')

    class MyPage(Page):
        pass
    client.load_plugin({"page": MyPage})
    assert client.get_class_list("page") == [Page, MyPage]


def test_get_class_fallthrough():
    client = Client('')

    class SometimesParagraph(ParagraphBlock):
        def __init__(self, client, notion_data, page=None, get_children=False):
            super().__init__(client, notion_data, page, get_children)
            if self.rich_text.to_plain_text() != "sometimes":
                raise UseNextClass()

    client.load_plugin({"blocks": {"paragraph": SometimesParagraph}})
    sometimes = client.wrap_notion_block(mock_paragraph_block([("sometimes", {})]), None, False)
    othertimes = client.wrap_notion_block(mock_paragraph_block([("othertimes", {})]), None, False)
    assert type(sometimes) == SometimesParagraph
    assert type(othertimes) == ParagraphBlock


def test_load_plugin_invalid_page_class():
    client = Client('')

    class MyPage:
        pass
    with pytest.raises(PluginError) as err:
        client.load_plugin({"page": MyPage})
    assert "MyPage" in str(err)


def test_load_plugin_valid_block():
    client = Client('')

    class MyParagraphBlock(ParagraphBlock):
        pass
    client.load_plugin({"blocks": {"paragraph": MyParagraphBlock}})
    assert client.get_class_list("blocks", "paragraph") == [ParagraphBlock, MyParagraphBlock]


def test_load_plugin_invalid_block_mapping():
    client = Client('')
    with pytest.raises(PluginError) as err:
        client.load_plugin({"blocks": str})
    assert "block" in str(err)


def test_load_plugin_invalid_block_class():
    client = Client('')

    class MyParagraphBlock:
        pass
    with pytest.raises(PluginError) as err:
        client.load_plugin({"blocks": {"paragraph": MyParagraphBlock}})
    assert "MyParagraphBlock" in str(err)

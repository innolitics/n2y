import pytest

from n2y.blocks import ParagraphBlock
from n2y.notion import Client
from n2y.page import Page
from n2y.errors import PluginError


def test_load_plugin_invalid_notion_object():
    client = Client('')
    with pytest.raises(PluginError) as err:
        client.load_plugin({"puppy": str})
    assert "puppy" in str(err)


def test_load_plugin_invalid_object_type():
    client = Client('')
    with pytest.raises(PluginError) as err:
        client.load_plugin({"block": {"puppy": str}})
    assert "block" in str(err)
    assert "puppy" in str(err)


def test_load_plugin_valid_page():
    client = Client('')
    assert client.get_class("page") == Page

    class MyPage(Page):
        pass
    client.load_plugin({"page": MyPage})
    assert client.get_class("page") == MyPage


def test_load_plugin_invalid_page_class():
    client = Client('')

    class MyPage:
        pass
    with pytest.raises(PluginError) as err:
        client.load_plugin({"page": MyPage})
    assert "MyPage" in str(err)


def test_load_plugin_valid_block():
    client = Client('')
    assert client.get_class("block", "paragraph") == ParagraphBlock

    class MyParagraphBlock(ParagraphBlock):
        pass
    client.load_plugin({"block": {"paragraph": MyParagraphBlock}})
    assert client.get_class("block", "paragraph") == MyParagraphBlock


def test_load_plugin_invalid_block_mapping():
    client = Client('')
    with pytest.raises(PluginError) as err:
        client.load_plugin({"block": str})
    assert "block" in str(err)


def test_load_plugin_invalid_block_class():
    client = Client('')

    class MyParagraphBlock:
        pass
    with pytest.raises(PluginError) as err:
        client.load_plugin({"block": {"paragraph": MyParagraphBlock}})
    assert "MyParagraphBlock" in str(err)

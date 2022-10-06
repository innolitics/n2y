import pytest

from n2y.notion import Client
from n2y.notion_mocks import mock_page

from pandoc.types import (
    Str, Para, Space, Code, Strikeout,
)


@pytest.fixture
def client():
    return Client('', plugins=None)


@pytest.fixture
def page(client):
    page_data = mock_page()
    return client.instantiate_class("page", None, client, page_data)


def test_from_pandoc_plain(client, page):
    pandoc_ast = Para([
        Str('This'), Space(), Str('is'), Space(), Str('the'), Space(),
        Str('first'), Space(), Str('test'), Space(), Str('string')
    ])
    client.save_block(page, pandoc_ast)
    new_block_ast = client.unsaved_blocks[page][-1].to_pandoc()
    assert pandoc_ast == new_block_ast


def test_from_pandoc_code_annotation(client, page):
    pandoc_ast = Para([
        Str('This'), Space(), Str('is'), Space(), Str('the'), Space(),
        Code(('', [], []), 'second test'), Space(), Str('string')
    ])
    client.save_block(page, pandoc_ast)
    new_block_ast = client.unsaved_blocks[page][-1].to_pandoc()
    assert pandoc_ast == new_block_ast


def test_from_pandoc_strikout_annotation(client, page):
    pandoc_ast = Para([
        Str('This'), Space(), Str('is'), Space(), Str('the'), Space(),
        Strikeout([Str('third'), Space(), Str('test')]), Space(), Str('string')
    ])
    client.save_block(page, pandoc_ast)
    new_block_ast = client.unsaved_blocks[page][-1].to_pandoc()
    assert pandoc_ast == new_block_ast

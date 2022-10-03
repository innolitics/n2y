
from n2y.notion import Client
from n2y.utils import id_from_share_link
from tests.utils import NOTION_ACCESS_TOKEN



url = "a36972712dd24d808bb0107bf0945f41"
token = "secret_aBbNlu5xsTtBNarAmuPYliS6pSCMpNaIJkcsz5eFuZn"
client = Client(token, plugins=None)
object_id = id_from_share_link(url)
page = client.get_page_or_database(object_id)

def test_from_pandoc_1():
  pandoc_ast = page.block.children[-1].to_pandoc()
  client.save_block(page, pandoc_ast)
  new_block_ast = client.unsaved_blocks[page][-1].to_pandoc()
  assert pandoc_ast == new_block_ast

def test_from_pandoc_2():
  pandoc_ast = page.block.children[-2].to_pandoc()
  client.save_block(page, pandoc_ast)
  new_block_ast = client.unsaved_blocks[page][-1].to_pandoc()
  assert pandoc_ast == new_block_ast

def test_from_pandoc_3():
  pandoc_ast = page.block.children[-3].to_pandoc()
  client.save_block(page, pandoc_ast)
  new_block_ast = client.unsaved_blocks[page][-1].to_pandoc()
  assert pandoc_ast == new_block_ast
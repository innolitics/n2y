
from n2y.notion import Client
from n2y.utils import id_from_share_link
from tests.utils import NOTION_ACCESS_TOKEN


def test_from_pandoc():
  url = "cfa8ff07bba244c8b967c9b6a7a954c1"
  client = Client(NOTION_ACCESS_TOKEN, plugins=None)
  object_id = id_from_share_link(url)
  page = client.get_page_or_database(object_id)
  pandoc_ast = page.to_pandoc()
  client.save_block(page, pandoc_ast)
  assert 1 == 0
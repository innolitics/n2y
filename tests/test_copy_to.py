
from n2y.notion import Client
from tests.utils import NOTION_ACCESS_TOKEN


def test_copy_to_paragraphs_and_nested_lists():
    client = Client(NOTION_ACCESS_TOKEN)
    destination_page_id = 'f488a7773d4546bca89c8bbfa5aafb79'
    current_page_id = 'c9e17a34da6a4b3295f82a1ad05bc3d8'
    page_data = {
        'parent': {'page_id': destination_page_id},
        'properties': {'title': [{'text': {'content': 'Temp_Page'}}]}
    }
    try:
        page_data = client.create_notion_page(page_data)
        assert page_data['object'] == 'page'
        page_id = page_data['id']
        original_page = client.get_page(current_page_id)
        original_page.block.children.copy_to(page_id)
        copied_page = client.get_page(page_id)
        assert [child.notion_data for child in original_page.block.children]\
            == [child.notion_data for child in copied_page.block.children]
    finally:
        client.delete_block(page_id)

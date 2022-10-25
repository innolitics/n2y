from n2y.notion import Client
from tests.utils import NOTION_ACCESS_TOKEN


def test_copy_to():
    client = Client(NOTION_ACCESS_TOKEN)
    destination_page_id = 'f488a7773d4546bca89c8bbfa5aafb79'
    current_page_id = '0b25a11e78b348c993b4dcf869f25a91'
    page_data = {
        'parent': {'page_id': destination_page_id},
        'properties': {'title': [{'text': {'content': 'Temp_Page'}}]}
    }
    try:
        page_data = client.create_notion_page(page_data)
        assert page_data['object'] == 'page'
        page_id = page_data['id']
        destination_page = client.get_page(page_id)
        original_page = client.get_page(current_page_id)
        copied_page = original_page.block.children.copy_to(destination_page)
        for i, copied_child in enumerate(copied_page.block.children):
            original_child = original_page.block.children[i]
            og_notion = {**original_child.notion_data}
            copy_notion = {**copied_child.notion_data}
            if original_child.notion_type == 'image' and copied_child.notion_type == 'image':
                default_img = ('https://i1.wp.com/cornellsun.com/wp-content/uploads/2020/06/159'
                '1119073-screen_shot_2020-06-02_at_10.30.13_am.png?fit=700%2C652&ssl=1')
                if copy_notion['external']['url'] == default_img:
                    copy_notion = og_notion
            assert og_notion == copy_notion
    finally:
        client.delete_block(page_id)

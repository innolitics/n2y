from n2y.notion import Client
from tests.utils import NOTION_ACCESS_TOKEN


destination_page_id = 'c9e17a34da6a4b3295f82a1ad05bc3d8'

current_page_id = '0b25a11e78b348c993b4dcf869f25a91'

default_file = (
    'https://i1.wp.com/cornellsun.com/wp-content/uploads/2020/06/159'
    '1119073-screen_shot_2020-06-02_at_10.30.13_am.png?fit=700%2C652&ssl=1'
)

default_pdf = (
    'https://reportstream.cdc.gov/assets/pdf/Report'
    'Stream-Programmers-Guide-v2.3-updated.pdf'
)

notion_data = {
    'parent': {'page_id': destination_page_id},
    'properties': {'title': [{'text': {'content': 'Temp_Page'}}]}
}


def image_or_file_is_valid(original_child, copied_child):
    both_are_images = original_child.notion_type == 'image' and copied_child.notion_type == 'image'
    both_are_files = original_child.notion_type == 'file' and copied_child.notion_type == 'file'
    if both_are_images or both_are_files:
        if copied_child.notion_data['external']['url'] == default_file:
            return True
    return False


def test_copy_to():
    client = Client(NOTION_ACCESS_TOKEN)
    page_data = client.create_notion_page(notion_data)
    assert page_data['object'] == 'page'
    page_id = page_data['id']
    try:
        destination_page = client.get_page(page_id)
        original_page = client.get_page(current_page_id)
        copied_page = original_page.block.children.copy_to(destination_page)
        for i, copied_child in enumerate(copied_page.block.children):
            original_child = original_page.block.children[i]
            og_notion = {**original_child.notion_data}
            copy_notion = {**copied_child.notion_data}
            if image_or_file_is_valid(original_child, copied_child):
                copy_notion = og_notion
            elif original_child.notion_type == 'pdf' and copied_child.notion_type == 'pdf':
                if copy_notion['external']['url'] == default_pdf:
                    copy_notion = og_notion
            elif original_child.notion_type == 'synced_block' and \
            copied_child.notion_type == 'synced_block': # noqa: E122
                if not copy_notion['synced_from']:
                    copy_notion = og_notion
            assert og_notion == copy_notion
    finally:
        client.delete_block(page_id)

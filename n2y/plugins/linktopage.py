import logging

from n2y.blocks import Block

logger = logging.getLogger(__name__)

class LinkToPage(Block):
    """
    Replace page link with the content of the linked-to page.

    """
    def __init__(self, client, notion_data, page, get_children=False):

        super().__init__(client, page, notion_data, get_children)

    def to_pandoc(self):
        assert self.linked_page_id is not None

        try:
            self.client.get_page(self.linked_page_id) 
            # Although out of the scope of the project at hand, get_page_or_database() 
            # could be used in place of get_page, to cover the linked database case. 
            # Might be an unnecessary step here. 
            self.rich_text = self.client.wrap_notion_rich_text_array(self.notion_data["rich_text"], self)

            # It's all about calling the proper method. 
            content = self.rich_text.to_pandoc()

        except PermissionError:
            msg = 'Permission denied when attempting to access linked page having id [%s]'
            logger.warning(msg, self.notion_data)


notion_classes = {
    "blocks": {
        "link_to_page": LinkToPage,
    }
}

import logging

from n2y.blocks import LinkToPageBlock

logger = logging.getLogger(__name__)


class LinkToPage(LinkToPageBlock):
    """
    Replace page link with the content of the linked-to page.

    """

    def __init__(self, client, notion_data, page, get_children=True):

        super().__init__(client, page, notion_data, get_children)

        # The type of object link can be either "page_id" or "database_id"
        self.link_type = self.notion_data["type"]
        self.linked_page_id = self.notion_data[self.link_type]
        self.linking_page_id = self.page.notion_id

    def to_pandoc(self):
        assert self.linked_page_id is not None

        # TODO: Might be expanded to handle links to databases as well.
        if self.link_type == "page_id":

            try:
                page = self.client.get_page_or_database(self.linked_page_id)

                rich_text = self.client.wrap_notion_rich_text_array(
                    page.notion_data["rich_text"], self)

            except PermissionError:
                msg = (
                    "Permission denied when attempting to access linked page having id [%s]"
                )
                logger.warning(msg, self.linked_page_id)
                return None

            return rich_text.to_pandoc()

        else:

            logger.warning(
                'Links to databases (to:%s from:%s) not supported at this time.',
                self.linked_page_id, self.linking_page_id
            )

            return None


notion_classes = {
    "blocks": {
        "link_to_page": LinkToPage,
    }
}

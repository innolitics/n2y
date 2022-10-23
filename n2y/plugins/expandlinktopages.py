import logging

from n2y.blocks import LinkToPageBlock

logger = logging.getLogger(__name__)


class ExpandingLinkToPageBlock(LinkToPageBlock):
    """
    Replace page link with the content of the linked-to page.

    """

    def to_pandoc(self):
        assert self.linked_node_id is not None

        if self.link_type == "page_id":
            page = self.client.get_page(self.linked_node_id)
            # The `page.block` refers to the ChildPageBlock in the page; we don't
            # want to call `to_pandoc` on it directly, since we don't want a
            # full pandoc document, but just the content that would have been in
            # that document.
            return page.block.children_to_pandoc()
        else:
            # TODO: Might be expanded to handle links to databases as well.
            logger.warning(
                'Links to databases (to:%s from:%s) not supported at this time.',
                self.linked_node_id, self.page.notion_id
            )
            return None


notion_classes = {
    "blocks": {
        "link_to_page": ExpandingLinkToPageBlock,
    }
}

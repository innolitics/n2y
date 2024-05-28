from unittest.mock import patch

from n2y.blocks import LinkToPageBlock


class ExpandingLinkToPageBlock(LinkToPageBlock):
    """
    Replace page link with the content of the linked-to page.

    """

    def to_pandoc(self):
        assert self.linked_node_id is not None

        if self.link_type == "page_id":
            # This `with` statement ensures that the parent page of the blocks on the linked page
            # is set to the parent page of the `ExpandingLinkToPageBlock` and not the linked page
            # itself.
            with patch.object(self.client, "get_child_blocks", self._get_child_blocks()):
                page = self.client.get_page(self.linked_node_id)
                # The `page.block` refers to the ChildPageBlock in the page; we don't
                # want to call `to_pandoc` on it directly, since we don't want a
                # full pandoc document, but just the content that would have been in
                # that document.
                return page.block.children_to_pandoc()
        else:
            # TODO: Might be expanded to handle links to databases as well.
            self.client.logger.warning(
                "Links to databases (to:%s from:%s) not supported at this time.",
                self.linked_node_id,
                self.page.notion_id,
            )
            return None

    def _get_child_blocks(self):
        """
        returns a function that operates like `n2y.notion.Client.get_child_blocks
        but sets the `page` argument as the `self.page` of this block.
        """

        def func(block_id, _, get_children):
            child_notion_blocks = self.client.get_child_notion_blocks(block_id)
            return [
                self.client.wrap_notion_block(b, self.page, get_children)
                for b in child_notion_blocks
            ]

        return func


notion_classes = {
    "blocks": {
        "link_to_page": ExpandingLinkToPageBlock,
    }
}

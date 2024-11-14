import typing
import urllib.parse
import uuid

from n2y.blocks import Block
from n2y.errors import UseNextClass
from n2y.rich_text import TextRichText
from n2y.utils import header_id_from_text


def get_notion_id_from_href(href: str) -> typing.Optional[str]:
    """Extract the ID of a target block from a href fragment"""
    target_id = urllib.parse.urlparse(href, allow_fragments=True).fragment
    if target_id is None:
        return None
    # Convert to UUID and back to ensure the format is correct
    try:
        return str(uuid.UUID(target_id))
    except ValueError:
        # fragment is not a Notion ID
        return None


def is_internal_link(href: typing.Optional[str], notion_id: str) -> bool:
    """Is the href fragment a link to a block on the same page?"""
    return href is not None and href.startswith(f"/{notion_id.replace('-', '')}")


def find_target_block(block: Block, target_id: str) -> Block:
    """Recursively search for a block with a given ID"""
    if block.notion_id == target_id:
        return block
    if block.children is None:
        return None
    for child in block.children:
        if isinstance(child, Block):
            target = find_target_block(child, target_id)
            if target is not None:
                return target
    return None


# def find_target_block(page: Page, target_id: str) -> Block:
#     page_block: ChildPageBlock = page.block
#     if page_block is None:
#         raise ValueError("Page.block is None")

#     try:
#         return next(
#             child for child in page_block.children if child.notion_id == target_id
#         )
#     except StopIteration:
#         logger.error(f"Page missing block with target id '{target_id}'")
#         raise


class NotionInternalLink(TextRichText):
    """This plugin fixes internal links to headers on the same page.

    Instead of leaving the link to point to the original notion source page,
    it substitutes the link to instead be the ID of the header.
    """

    def __init__(self, client, notion_data, block=None):
        super().__init__(client, notion_data, block)
        if block is None or not is_internal_link(self.href, self.block.page.notion_id):
            raise UseNextClass

    def to_pandoc(self):
        target_id = get_notion_id_from_href(self.href)
        if target_id is None:
            self.client.logger.warning(
                "Internal link missing; defaulting to link with no-op behavior"
            )
            return super().to_pandoc()

        target_block = find_target_block(self.block.page.block, target_id)
        if target_block is None:
            self.client.logger.error(
                f"Internal link target block not found: {target_id}"
            )
            # Fallback to default behavior for TextRichText conversion
            return super().to_pandoc()
        header_id = header_id_from_text(target_block.rich_text.to_plain_text())
        self.href = f"#{header_id}"
        return super().to_pandoc()


notion_classes = {"rich_texts": {"text": NotionInternalLink}}

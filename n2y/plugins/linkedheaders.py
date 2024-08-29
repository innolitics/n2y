from pandoc.types import Header, Link

from n2y.blocks import HeadingBlock
from n2y.utils import header_id_from_text


class LinkedHeadingBlock(HeadingBlock):
    """
    Make headers have links back to the originating notion block.
    """

    def to_pandoc(self):
        section_id = header_id_from_text(self.rich_text.to_plain_text())
        link = [Link(("", [], []), self.rich_text.to_pandoc(), (self.notion_url, ""))]
        return Header(self.level, (section_id, [], []), link)


class LinkedHeadingThreeBlock(LinkedHeadingBlock):
    level = 3


class LinkedHeadingTwoBlock(LinkedHeadingBlock):
    level = 2


class LinkedHeadingOneBlock(LinkedHeadingBlock):
    level = 1


notion_classes = {
    "blocks": {
        "heading_1": LinkedHeadingOneBlock,
        "heading_2": LinkedHeadingTwoBlock,
        "heading_3": LinkedHeadingThreeBlock,
    }
}

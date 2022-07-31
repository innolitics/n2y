from n2y.blocks import HeadingThreeBlock, HeadingTwoBlock, HeadingOneBlock

from pandoc.types import Header, Link


class LinkedHeadingBlock:
    """
    Replace headers with links back to the originating notion block.
    """

    def to_pandoc(self):
        link = [Link(
            ('', [], []),
            self.rich_text.to_pandoc(),
            (self.notion_url, '')
        )]
        return Header(self.level, ('', [], []), link)


class LinkedHeadingThreeBlock(HeadingThreeBlock, LinkedHeadingBlock):
    pass


class LinkedHeadingTwoBlock(HeadingTwoBlock, LinkedHeadingBlock):
    pass


class LinkedHeadingOneBlock(HeadingOneBlock, LinkedHeadingBlock):
    pass


notion_classes = {
    "blocks": {
        "heading_1": LinkedHeadingOneBlock,
        "heading_2": LinkedHeadingTwoBlock,
        "heading_3": LinkedHeadingThreeBlock,
    }
}

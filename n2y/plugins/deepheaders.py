import re

from n2y.blocks import HeadingThreeBlock
from n2y.errors import UseNextClass


class DeepHeadersBlock(HeadingThreeBlock):
    """
    Adds support for deeper headers in Notion (i.e., and h4, h5, h6, etc.).

    Any header 3 that begins with one or more "=" followed by a " " will be
    replaced with a deeper header. For example, a notion header 3 block that
    begins with "== Header" will become an h5 and the "== " will be stripped.
    """
    trigger_regex = re.compile(r'^(=+) ')

    def __init__(self, client, notion_data, page, get_children=True):
        super().__init__(client, notion_data, page, get_children)
        result = self.rich_text.matches(self.trigger_regex)
        if result:
            number_of_equal_signs = len(result.group(1))
            self.level += number_of_equal_signs
            self.rich_text.lstrip(result.group(0))
        else:
            raise UseNextClass()


notion_classes = {
    "blocks": {
        "heading_3": DeepHeadersBlock,
    }
}

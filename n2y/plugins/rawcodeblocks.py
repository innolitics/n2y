import re

from pandoc.types import RawBlock, Format

from n2y.blocks import FencedCodeBlock
from n2y.errors import UseNextClass


class RawFencedCodeBlock(FencedCodeBlock):
    """
    Adds support for raw codeblocks.

    Any code block whose caption begins with "{=language}" will be made into a
    raw block for pandoc to parse. This is useful if you need to drop into Raw
    HTML or other formats.

    See https://pandoc.org/MANUAL.html#generic-raw-attribute
    """
    trigger_regex = re.compile(r'^{=(.+)}')

    def __init__(self, client, notion_data, page, get_children=True):
        super().__init__(client, notion_data, page, get_children)
        result = self.caption.matches(self.trigger_regex)
        if result:
            self.raw_lang = result.group(1)
        else:
            raise UseNextClass()

    def to_pandoc(self):
        return RawBlock(Format(self.raw_lang), self.rich_text.to_plain_text())


notion_classes = {
    "blocks": {
        "code": RawFencedCodeBlock,
    }
}

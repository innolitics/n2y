from itertools import groupby
import logging
import importlib.util
from os import path

from pandoc.types import (
    Str, Para, Plain, Header, CodeBlock, BulletList, OrderedList, Decimal,
    Period, Meta, Pandoc, Link, HorizontalRule, BlockQuote, Image, MetaString,
    Table, TableHead, TableBody, TableFoot, RowHeadColumns, Row, Cell, RowSpan,
    ColSpan, ColWidthDefault, AlignDefault, Caption, Math, DisplayMath,
)


# Notes:
# A single Notion block may have multiple lines of text.
# A page is a block that puts children into its "content" attribute.
# We transform page blocks into other block types.
#
# Pandoc makes each word a block, and spaces are blocks too!
#
# Block types used here that do not exist in Notion:
#   container - block with no top-level content, only children (used to parse a page and lists)
#   bulleted_list - Notion has bulleted_list_item, but no enclosing container
#   numbered_list - Notion has numbered_list_item, but no enclusing container


logger = logging.getLogger(__name__)


def load_plugins(filename):
    # TODO: Consider storing the imported classes on the `Client` instance. This
    # will make it easier to test the plugin system in isolation, since given
    # that the plugins are globals right now, if we have a test that uses the
    # plugins it will mutate the global module state. Furthermore, by moving the
    # plugin block class references onto the `Client` class it will make it
    # easier to dynamically enable or disable certain plugin classes for certain
    # notion pages, which is a feature we will likely need in the future.

    # TODO: Make it possible to swap out the RichText classes too

    # TODO: Make it possible to modify the property value code too; note that we
    # should probably create a hierarchy of classes, similar to how the Block
    # classes work

    abs_path = path.abspath(filename)
    plugin_spec = importlib.util.spec_from_file_location("plugins", abs_path)
    plugin_module = importlib.util.module_from_spec(plugin_spec)
    plugin_spec.loader.exec_module(plugin_module)
    for (key, value) in plugin_module.exports.items():
        if key in globals():
            class_to_replace = globals()[key]
            plugin_base_class_names = [b.__name__ for b in value.__bases__]
            # plugins can only override classes in this file that are derrived from a Block
            if class_to_replace.__name__ in plugin_base_class_names \
                    and issubclass(class_to_replace, Block):
                globals()[key] = value
            else:
                logger.warning(
                    'Cannot import plugin "%s" because it is not '
                    'derrived from a known class.', key)
        else:
            raise NotImplementedError(f'Unknown plugin type "{key}".')


class Block:
    def __init__(self, client, notion_block, get_children=True):
        """
        The Notion client object is passed down for the following reasons:
        1. Some child objects may be unknown until the block is processed.
           Links to other Notion pages are an example.
        2. In some cases a block may choose not to get child blocks.
           Currently, all blocks load all children.
        """
        logger.debug('Instantiating "%s" block', type(self).__name__)
        self.client = client

        self.notion_id = notion_block['id']
        self.created_time = notion_block['created_time']
        self.created_by = notion_block['created_by']
        self.last_edited_time = notion_block['last_edited_time']
        self.last_edited_by = notion_block['last_edited_by']
        self.has_children = notion_block['has_children']
        self.archived = notion_block['archived']
        self.notion_type = notion_block['type']
        self.notion_data = notion_block[notion_block['type']]

        if get_children:
            if self.has_children:
                children = self.client.get_child_blocks(self.notion_id, get_children)
            else:
                children = []
        else:
            children = None
        self.children = children

    def to_pandoc(self):
        raise NotImplementedError()

    def children_to_pandoc(self):
        assert self.has_children
        pandoc_ast = []
        for block_type, blocks in groupby(self.children, lambda c: type(c)):
            if issubclass(block_type, ListItemBlock):
                pandoc_ast.append(block_type.list_to_pandoc(blocks))
            else:
                pandoc_ast.extend(b.to_pandoc() for b in blocks)
        return pandoc_ast


class ListItemBlock(Block):
    @classmethod
    def list_to_pandoc(klass, items):
        raise NotImplementedError()


class ChildPageBlock(Block):
    def __init__(self, client, block, get_children=True):
        super().__init__(client, block, get_children)
        self.title = self.notion_data["title"]

    def to_pandoc(self):
        assert self.children is not None
        if self.children:
            children = self.children_to_pandoc()
            return Pandoc(Meta({'title': MetaString(self.title)}), children)
        else:
            return None


class EquationBlock(Block):
    def __init__(self, client, block, get_children=True):
        super().__init__(client, block, get_children)
        self.expression = self.notion_data["expression"]

    def to_pandoc(self):
        return Para([Math(DisplayMath(), self.expression)])


class ParagraphBlock(Block):
    def __init__(self, client, block, get_children=True):
        super().__init__(client, block, get_children)
        self.text = client.wrap_notion_rich_text_array(self.notion_data["text"])

    def to_pandoc(self):
        content = self.text.to_pandoc()
        if self.has_children:
            result = [Para(content)]
            children = self.children_to_pandoc()
            result.extend(children)
        else:
            result = Para(content)
        return result


class BulletedListItemBlock(ListItemBlock):
    def __init__(self, client, block, get_children=True):
        super().__init__(client, block, get_children)
        self.text = client.wrap_notion_rich_text_array(self.notion_data["text"])

    def to_pandoc(self):
        content = [Plain(self.text.to_pandoc())]
        if self.has_children:
            children = self.children_to_pandoc()
            content.extend(children)
        return content

    @classmethod
    def list_to_pandoc(klass, blocks):
        return BulletList([b.to_pandoc() for b in blocks])


class ToDoListItemBlock(BulletedListItemBlock):
    def __init__(self, client, block, get_children=True):
        super().__init__(client, block, get_children)
        self.checked = self.notion_data['checked']
        if self.checked:
            self.text.items[0].plain_text.text = '☒ ' + self.text.items[0].plain_text.text
        else:
            self.text.items[0].plain_text.text = '☐ ' + self.text.items[0].plain_text.text


class NumberedListItemBlock(ListItemBlock):
    def __init__(self, client, block, get_children=True):
        super().__init__(client, block, get_children)
        self.text = client.wrap_notion_rich_text_array(self.notion_data['text'])

    def to_pandoc(self):
        content = [Plain(self.text.to_pandoc())]
        if self.has_children:
            children = self.children_to_pandoc()
            content.extend(children)
        return content

    @classmethod
    def list_to_pandoc(klass, blocks):
        return OrderedList((1, Decimal(), Period()), [b.to_pandoc() for b in blocks])


class HeadingBlock(Block):
    def __init__(self, client, block, get_children=True):
        super().__init__(client, block, get_children)
        self.text = client.wrap_notion_rich_text_array(self.notion_data["text"])

    def to_pandoc(self):
        return Header(self.level, ('', [], []), self.text.to_pandoc())


class HeadingOneBlock(HeadingBlock):
    level = 1


class HeadingTwoBlock(HeadingBlock):
    level = 2


class HeadingThreeBlock(HeadingBlock):
    level = 3


class DividerBlock(Block):
    def to_pandoc(self):
        return HorizontalRule()


class BookmarkBlock(Block):
    def __init__(self, client, block, get_children=True):
        super().__init__(client, block, get_children)
        self.url = self.notion_data["url"]
        if self.notion_data["caption"]:
            self.caption = client.wrap_notion_rich_text_array(self.notion_data["caption"])
        else:
            self.caption = None

    def to_pandoc(self):
        if self.caption:
            caption_ast = self.caption.to_pandoc()
        else:
            caption_ast = [Str(self.url)]
        return Para([Link(('', [], []), caption_ast, (self.url, ''))])


class FencedCodeBlock(Block):
    def __init__(self, client, block, get_children=True):
        super().__init__(client, block, get_children)
        self.language = self.notion_data["language"]
        self.text = client.wrap_notion_rich_text_array(self.notion_data["text"])

    def to_pandoc(self):
        plain_text = ''.join(t.plain_text.text for t in self.text.items)
        return CodeBlock(('', [self.language], []), plain_text)


class QuoteBlock(Block):
    def __init__(self, client, block, get_children=True):
        super().__init__(client, block, get_children)
        self.text = client.wrap_notion_rich_text_array(self.notion_data["text"])

    def to_pandoc(self):
        return BlockQuote([Para(self.text.to_pandoc())])


class ImageBlock(Block):
    def __init__(self, client, block, get_children=True):
        super().__init__(client, block, get_children)
        self.file = File(client, block['image'])
        self.caption = client.wrap_notion_rich_text_array(self.notion_data["caption"])

    def to_pandoc(self):
        url = None
        if self.file.type == "external":
            url = self.file.url
        elif self.file.type == "file":
            url = self.file.download()
        return Para([Image(('', [], []), self.caption.to_pandoc(), (url, ''))])


class TableBlock(Block):
    def __init__(self, client, block, get_children=True):
        super().__init__(client, block, get_children)
        self.has_column_header = self.notion_data['has_column_header']
        self.has_row_header = self.notion_data['has_row_header']
        self.table_width = self.notion_data['table_width']

    def to_pandoc(self):
        children = self.children_to_pandoc()
        # Isolate the header row if it exists
        if self.has_column_header:
            header_rows = [children.pop(0)]
        else:
            header_rows = []
        if self.has_row_header:
            row_header_columns = 1
        else:
            row_header_columns = 0
        # Notion does not have cell alignment or width options, sticking with defaults.
        colspec = [(AlignDefault(), ColWidthDefault()) for _ in range(self.table_width)]
        table = Table(
            ('', [], []),
            Caption(None, []),
            colspec,
            TableHead(('', [], []), header_rows),
            [TableBody(
                ('', [], []),
                RowHeadColumns(row_header_columns),
                [],
                children
            )],
            TableFoot(('', [], []), [])
        )
        return table


class RowBlock(Block):
    def __init__(self, client, block, get_children=True):
        super().__init__(client, block, get_children)
        self.cells = [client.wrap_notion_rich_text_array(
            cell) for cell in self.notion_data["cells"]]

    def to_pandoc(self):
        cells = [Cell(
            ('', [], []),
            AlignDefault(),
            RowSpan(1),
            ColSpan(1),
            [Plain(cell.to_pandoc())]
        ) for cell in self.cells]
        return Row(('', [], []), cells)


class ToggleBlock(Block):
    """
    Generates a bulleted list item with indented children. A plugin may be used
    to add html classes and replicate the interactive behavior found in Notion.
    """

    def __init__(self, client, block, get_children=True):
        super().__init__(client, block, get_children)
        self.text = client.wrap_notion_rich_text_array(self.notion_data["text"])

    def to_pandoc(self):
        header = self.text.to_pandoc()
        children = self.children_to_pandoc()
        content = [Para(header)]
        content.extend(children)
        return BulletList([content])


class CalloutBlock(Block):
    def __init__(self, client, block, get_children=True):
        super().__init__(client, block, get_children)
        self.text = client.wrap_notion_rich_text_array(self.notion_data["text"])

    def to_pandoc(self):
        content = self.text.to_pandoc()
        if self.has_children:
            children = self.children_to_pandoc()
            result = [Para(content)]
            result.extend(children)
        else:
            result = Para(content)
        return result


DEFAULT_BLOCKS = {
    "child_page": ChildPageBlock,
    "paragraph": ParagraphBlock,
    "heading_1": HeadingOneBlock,
    "heading_2": HeadingTwoBlock,
    "heading_3": HeadingThreeBlock,
    "divider": DividerBlock,
    "numbered_list_item": NumberedListItemBlock,
    "bulleted_list_item": BulletedListItemBlock,
    "to_do": ToDoListItemBlock,
    "bookmark": BookmarkBlock,
    "image": ImageBlock,
    "code": FencedCodeBlock,
    "quote": QuoteBlock,
    "table": TableBlock,
    "table_row": RowBlock,
    "toggle": ToggleBlock,
    "equation": EquationBlock,
    "callout": CalloutBlock,
}
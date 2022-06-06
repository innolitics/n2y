from itertools import groupby
import logging
from os import path
from urllib.parse import urlparse

from pandoc.types import (
    Str, Para, Plain, Header, CodeBlock, BulletList, OrderedList, Decimal,
    Period, Meta, Pandoc, Link, HorizontalRule, BlockQuote, Image, MetaString,
    Table, TableHead, TableBody, TableFoot, RowHeadColumns, Row, Cell, RowSpan,
    ColSpan, ColWidthDefault, AlignDefault, Caption, Math, DisplayMath,
)


logger = logging.getLogger(__name__)


class Block:
    """
    A Notion page's content consists of a tree of nested Blocks.

    See here for a listing of all of them: https://developers.notion.com/reference/block

    This class that wraps the Notion blocks and also is responsible for
    transforming them into Pandoc abstract syntax tree. A single Notion block
    often has multiple lines of text.

    Pandoc's data model doesn't line up exactly with Notion's, for example
    Notion doesn't have a wrapper around lists, while Pandoc does.
    """

    def __init__(self, client, notion_data, get_children=True):
        """
        The Notion client object is passed down for the following reasons:
        1. Some child objects may be unknown until the block is processed.
           Links to other Notion pages are an example.
        2. In some cases a block may choose not to get child blocks.
           Currently, all blocks load all children.
        """
        logger.debug('Instantiating "%s" block', type(self).__name__)
        self.client = client

        self.notion_id = notion_data['id']
        self.created_time = notion_data['created_time']
        self.created_by = notion_data['created_by']
        self.last_edited_time = notion_data['last_edited_time']
        self.last_edited_by = notion_data['last_edited_by']
        self.has_children = notion_data['has_children']
        self.archived = notion_data['archived']
        self.notion_type = notion_data['type']
        self.notion_data = notion_data[notion_data['type']]

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
    def __init__(self, client, notion_data, get_children=True):
        super().__init__(client, notion_data, get_children)
        self.title = self.notion_data["title"]

    def to_pandoc(self):
        assert self.children is not None
        if self.children:
            children = self.children_to_pandoc()
            return Pandoc(Meta({'title': MetaString(self.title)}), children)
        else:
            return None


class EquationBlock(Block):
    def __init__(self, client, notion_data, get_children=True):
        super().__init__(client, notion_data, get_children)
        self.expression = self.notion_data["expression"]

    def to_pandoc(self):
        return Para([Math(DisplayMath(), self.expression)])


class ParagraphBlock(Block):
    def __init__(self, client, notion_data, get_children=True):
        super().__init__(client, notion_data, get_children)
        self.rich_text = client.wrap_notion_rich_text_array(self.notion_data["rich_text"])

    def to_pandoc(self):
        content = self.rich_text.to_pandoc()
        if self.has_children:
            result = [Para(content)]
            children = self.children_to_pandoc()
            result.extend(children)
        else:
            result = Para(content)
        return result


class BulletedListItemBlock(ListItemBlock):
    def __init__(self, client, notion_data, get_children=True):
        super().__init__(client, notion_data, get_children)
        self.rich_text = client.wrap_notion_rich_text_array(self.notion_data["rich_text"])

    def to_pandoc(self):
        content = [Plain(self.rich_text.to_pandoc())]
        if self.has_children:
            children = self.children_to_pandoc()
            content.extend(children)
        return content

    @classmethod
    def list_to_pandoc(klass, items):
        return BulletList([b.to_pandoc() for b in items])


class ToDoListItemBlock(BulletedListItemBlock):
    def __init__(self, client, notion_data, get_children=True):
        super().__init__(client, notion_data, get_children)
        self.checked = self.notion_data['checked']

        # TODO: Consider doing this at the "to_pandoc" stage
        box = '☒' if self.checked else '☐'
        self.rich_text.items[0].plain_text = box + \
            ' ' + self.rich_text.items[0].plain_text


class NumberedListItemBlock(ListItemBlock):
    def __init__(self, client, notion_data, get_children=True):
        super().__init__(client, notion_data, get_children)
        self.rich_text = client.wrap_notion_rich_text_array(self.notion_data["rich_text"])

    def to_pandoc(self):
        content = [Plain(self.rich_text.to_pandoc())]
        if self.has_children:
            children = self.children_to_pandoc()
            content.extend(children)
        return content

    @classmethod
    def list_to_pandoc(klass, items):
        return OrderedList((1, Decimal(), Period()), [b.to_pandoc() for b in items])


class HeadingBlock(Block):
    def __init__(self, client, notion_data, get_children=True):
        super().__init__(client, notion_data, get_children)
        self.rich_text = client.wrap_notion_rich_text_array(self.notion_data["rich_text"])

    def to_pandoc(self):
        return Header(self.level, ('', [], []), self.rich_text.to_pandoc())


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
    def __init__(self, client, notion_data, get_children=True):
        super().__init__(client, notion_data, get_children)
        self.url = self.notion_data["url"]
        self.caption = client.wrap_notion_rich_text_array(self.notion_data["caption"])

    def to_pandoc(self):
        if self.caption:
            caption_ast = self.caption.to_pandoc()
        else:
            caption_ast = [Str(self.url)]
        return Para([Link(('', [], []), caption_ast, (self.url, ''))])


class FencedCodeBlock(Block):
    def __init__(self, client, notion_data, get_children=True):
        super().__init__(client, notion_data, get_children)
        self.language = self.notion_data["language"]
        self.rich_text = client.wrap_notion_rich_text_array(self.notion_data["rich_text"])

    def to_pandoc(self):
        plain_text = ''.join(t.plain_text for t in self.rich_text.items)
        return CodeBlock(('', [self.language], []), plain_text)


class QuoteBlock(Block):
    def __init__(self, client, notion_data, get_children=True):
        super().__init__(client, notion_data, get_children)
        self.rich_text = client.wrap_notion_rich_text_array(self.notion_data["rich_text"])

    def to_pandoc(self):
        return BlockQuote([Para(self.rich_text.to_pandoc())])


class FileBlock(Block):
    def __init__(self, client, notion_data, get_children=True):
        super().__init__(client, notion_data, get_children)
        self.file = client.wrap_notion_file(notion_data['file'])
        self.caption = client.wrap_notion_rich_text_array(self.notion_data["caption"])

    def to_pandoc(self):
        url = None
        if self.file.type == "external":
            url = self.file.url
        elif self.file.type == "file":
            # TODO: log warning if there are name collisions
            # TODO: save files in a folder associated with the page
            file_path = path.basename(urlparse(self.file.url).path)
            url = self.client.download_file(self.file.url, file_path)
        if self.caption:
            caption_ast = self.caption.to_pandoc()
        else:
            caption_ast = [Str(url)]
        return Para([Link(('', [], []), caption_ast, (url, ''))])


class ImageBlock(Block):
    def __init__(self, client, notion_data, get_children=True):
        super().__init__(client, notion_data, get_children)
        self.file = client.wrap_notion_file(notion_data['image'])
        self.caption = client.wrap_notion_rich_text_array(self.notion_data["caption"])

    def to_pandoc(self):
        url = None
        if self.file.type == "external":
            url = self.file.url
        elif self.file.type == "file":
            # TODO: log warning if there are name collisions
            # TODO: save images in a folder associated with the page
            file_path = path.basename(urlparse(self.file.url).path)
            url = self.client.download_file(self.file.url, file_path)
        return Para([Image(('', [], []), self.caption.to_pandoc(), (url, ''))])


class TableBlock(Block):
    def __init__(self, client, notion_data, get_children=True):
        super().__init__(client, notion_data, get_children)
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
    def __init__(self, client, notion_data, get_children=True):
        super().__init__(client, notion_data, get_children)
        self.cells = [client.wrap_notion_rich_text_array(nc) for nc in self.notion_data["cells"]]

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

    def __init__(self, client, notion_data, get_children=True):
        super().__init__(client, notion_data, get_children)
        self.rich_text = client.wrap_notion_rich_text_array(self.notion_data["rich_text"])

    def to_pandoc(self):
        header = self.rich_text.to_pandoc()
        children = self.children_to_pandoc()
        content = [Para(header)]
        content.extend(children)
        return BulletList([content])


class CalloutBlock(Block):
    def __init__(self, client, notion_data, get_children=True):
        super().__init__(client, notion_data, get_children)
        self.rich_text = client.wrap_notion_rich_text_array(self.notion_data["rich_text"])

    def to_pandoc(self):
        content = self.rich_text.to_pandoc()
        if self.has_children:
            children = self.children_to_pandoc()
            result = [Para(content)]
            result.extend(children)
        else:
            result = Para(content)
        return result


DEFAULT_BLOCKS = {
    "paragraph": ParagraphBlock,
    "heading_1": HeadingOneBlock,
    "heading_2": HeadingTwoBlock,
    "heading_3": HeadingThreeBlock,
    "bulleted_list_item": BulletedListItemBlock,
    "numbered_list_item": NumberedListItemBlock,
    "to_do": ToDoListItemBlock,
    "toggle": ToggleBlock,
    "child_page": ChildPageBlock,
    # "child_database": ChildDatabaseBlock,
    # "embed": EmbedBlock,
    "image": ImageBlock,
    # "video": VideoBlock,
    "file": FileBlock,
    # "pdf": PdfBlock,
    "bookmark": BookmarkBlock,
    "callout": CalloutBlock,
    "quote": QuoteBlock,
    "equation": EquationBlock,
    "divider": DividerBlock,
    # "table_of_contents": TableOfContentsBlock,
    # "column": ColumnBlock,
    # "column_list": ColumnListBlock,
    # "link_preview": LinkPreviewBlock,
    # "synced_block": SyncedBlock,
    # "template": TemplateBlock,
    # "link_to_page": LinkToPageBlock,
    "code": FencedCodeBlock,
    "table": TableBlock,
    "table_row": RowBlock,
    # "unsupported": UnsupportedBlock,
}

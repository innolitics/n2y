import importlib.util
from os import path, makedirs
from shutil import copyfileobj
from urllib.parse import urlparse
import requests

from pandoc.types import Str, Para, Plain, Space, SoftBreak, Header, Strong, Emph, \
    Strikeout, Code, CodeBlock, BulletList, OrderedList, Decimal, Period, Meta, Pandoc, Link, \
    HorizontalRule, BlockQuote, Image, Underline, MetaString, Table, TableHead, TableBody, \
    TableFoot, RowHeadColumns, Row, Cell, RowSpan, ColSpan, ColWidthDefault, AlignDefault, \
    Caption, Math, InlineMath, DisplayMath
import re

from n2y.notion import Client


# Notes:
# A single Notion block may have multiple lines of text.
# A page is a block that puts children into "content" attribute.
# We transform page block to resemble other block types.
#
# Pandoc makes each word a block, and spaces are blocks too!
#
# Block types used here that do not exist in Notion:
#   container - block with no top-level content, only children (used to parse a page and lists)
#   bulleted_list - Notion has bulleted_list_item, but no enclosing container
#   numbered_list - Notion has numbered_list_item, but no enclusing container


IMAGE_PATH = None
IMAGE_WEB_PATH = None


def load_plugins(filename):
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
                print(f"Cannot import plugin \"{key}\" since it not derrived from a known class.")
        else:
            raise NotImplementedError(f"Unknown plugin type {key}.")


def load_block(client: Client, id, get_children=True):
    block = client.get_block(id)
    return parse_block(client, block, get_children)


# The Notion client object is passed down for the following reasons:
#   1. Some child objects may be unknown until the block is processed.
#      Links to other Notion pages are an example.
#   2. In some cases a block may choose not to get child blocks.
#      Currently, all blocks load all children.
def parse_block(client: Client, block, get_children=True):
    if block['type'] == "child_page":
        return ChildPageBlock(client, block, get_children)
    elif block['type'] == "paragraph":
        return ParagraphBlock(client, block, get_children)
    elif block['type'] == "heading_1":
        return HeadingOne(client, block, get_children)
    elif block['type'] == "heading_2":
        return HeadingTwo(client, block, get_children)
    elif block['type'] == "heading_3":
        return HeadingThree(client, block, get_children)
    elif block['type'] == "divider":
        return Divider(client, block, get_children)
    elif block['type'] == "bookmark":
        return Bookmark(client, block, get_children)
    elif block['type'] == "image":
        return ImageBlock(client, block, get_children)
    elif block['type'] == "code":
        return CodeBlockFenced(client, block, get_children)
    elif block['type'] == "quote":
        return Quote(client, block, get_children)
    elif block['type'] == "table":
        return TableBlock(client, block, get_children)
    elif block['type'] == "table_row":
        return RowBlock(client, block, get_children)
    elif block['type'] == "toggle":
        return Toggle(client, block, get_children)
    elif block['type'] == "equation":
        return Equation(client, block, get_children)
    else:
        # TODO: add remaining block types
        raise NotImplementedError(f"Unknown block type {block['type']}")


class Block():
    def __init__(self, client: Client, block, get_children=True):
        self.client = client
        # populate attributes
        for key, value in block.items():
            if key != block['type']:
                self.__dict__[key] = value

        # append attributes specific to block type
        for key, value in block[self.type].items():
            self.__dict__[key] = value

        if get_children:
            self.get_children()

    def to_pandoc(self):
        if self.has_children:
            return [c.to_pandoc() for c in self.children]

    def get_children(self):
        if self.has_children:
            self.children = []
            previous_child_type = ""
            for child in self.client.get_block_children(self.id, recursive=False):
                if child['type'] == "numbered_list_item":
                    if previous_child_type != "numbered_list_item":
                        self.children.append(NumberedList(self.client, {}, get_children=False))
                    self.children[-1].append(NumberedListItem(self.client, child))
                elif child['type'] == "bulleted_list_item":
                    if previous_child_type != "bulleted_list_item":
                        self.children.append(BulletedList(self.client, {}, get_children=False))
                    self.children[-1].append(BulletedListItem(self.client, child))
                elif child['type'] == "to_do":
                    if previous_child_type != "to_do":
                        self.children.append(ToDo(self.client, {}, get_children=False))
                    self.children[-1].append(ToDoItem(self.client, child))
                else:
                    self.children.append(parse_block(self.client, child, get_children=True))

                previous_child_type = child['type']


class PlainText():
    def __init__(self, text):
        self.text = text

    def to_pandoc(self):
        """Tokenize the text"""
        ast = []
        match = re.findall(r"( +)|(\S+)|(\n+)|(\t+)", self.text)

        for m in match:
            space, word, newline, tab = m
            for _ in range(len(space)):
                ast.append(Space())
            if word:
                ast.append(Str(word))
            for _ in range(len(newline)):
                ast.append(SoftBreak())
            for _ in range(len(tab) * 4):  # 4 spaces per tab
                ast.append(Space())
        return ast


class Annotations():
    def __init__(self, block):
        for key, value in block.items():
            self.__dict__[key] = value

    def apply_pandoc(self, target):
        result = target
        if self.code:
            result = [Code(("", [], []), result)]
        if self.bold:
            result = [Strong(result)]
        if self.italic:
            result = [Emph(result)]
        if self.underline:
            result = [Underline(result)]
        if self.strikethrough:
            result = [Strikeout(result)]
        return result


class InlineEquation():
    def __init__(self, block):
        for key, value in block.items():
            self.__dict__[key] = value

    def to_pandoc(self):
        return [Math(InlineMath(), self.expression)]


class RichText():
    def __init__(self, block):
        handlers = {
            'annotations': Annotations,
            'plain_text': PlainText,
            'equation': InlineEquation}
        for key, value in block.items():
            if key in handlers.keys():
                self.__dict__[key] = handlers[key](value)
            else:
                self.__dict__[key] = value

    def to_pandoc(self):
        if self.type == 'text':
            if self.annotations.code:
                # Send raw text if it's code.
                return self.annotations.apply_pandoc(self.plain_text.text)
            elif 'href' in self.__dict__ and self.href:
                # links
                return [Link(('', [], []),
                             self.annotations.apply_pandoc(self.plain_text.to_pandoc()),
                             (self.href, ''))]
            else:
                # regular text
                return self.annotations.apply_pandoc(self.plain_text.to_pandoc())
        elif self.type == 'equation':
            return self.equation.to_pandoc()
        else:
            raise NotImplementedError(f"Unknown rich text object type: {self.type}")


class RichTextArray():
    def __init__(self, text):

        self.text = [RichText(i) for i in text]

    def to_pandoc(self):
        return sum([item.to_pandoc() for item in self.text], [])


class ChildPageBlock(Block):
    def to_pandoc(self):
        if hasattr(self, 'children'):
            children = [item.to_pandoc() for item in self.children]
            return Pandoc(Meta({'title': MetaString(self.title)}), children)
        else:
            return None


class Equation(Block):
    def __init__(self, client: Client, block, get_children=True):
        super().__init__(client, block, get_children)

    def to_pandoc(self):
        content = [Math(DisplayMath(), self.expression)]
        return Para(content)


class ParagraphBlock(Block):
    def __init__(self, client: Client, block, get_children=True):
        super().__init__(client, block, get_children)
        self.text = RichTextArray(self.text)

    def to_pandoc(self):
        content = self.text.to_pandoc()
        children = super().to_pandoc()
        if children:
            result = [Para(content)]
            result.extend(children)
            return result
        else:
            return Para(content)


class BulletedListItem(Block):
    def __init__(self, client: Client, block, get_children=True):
        super().__init__(client, block, get_children)
        self.text = RichTextArray(self.text)

    def to_pandoc(self):
        content = [Plain(self.text.to_pandoc())]
        children = super().to_pandoc()
        if children:
            content.extend(children)
        return content


class BulletedList(Block):
    def __init__(self, client: Client, block, get_children=True):
        self.client = client
        self.has_children = False
        self.items = []
        self.created_time = None
        self.last_edited_time = None
        self.type = "bulleted_list"
        self.id = None

    def append(self, item: BulletedListItem):
        self.items.append(item)

    def to_pandoc(self):
        return BulletList([i.to_pandoc() for i in self.items])


class ToDoItem(BulletedListItem):
    def __init__(self, client: Client, block, get_children=True):
        self.type = 'to_do_list'
        super().__init__(client, block, get_children)
        if self.checked:
            self.text.text[0].plain_text.text = '☒ ' + self.text.text[0].plain_text.text
        else:
            self.text.text[0].plain_text.text = '☐ ' + self.text.text[0].plain_text.text


class ToDo(BulletedList):
    def __init__(self, client: Client, block, get_children=True):
        self.type = 'to_do_list'
        super().__init__(client, block, get_children)


class NumberedListItem(Block):
    def __init__(self, client: Client, block, get_children=True):
        super().__init__(client, block, get_children)
        self.text = RichTextArray(self.text)

    def to_pandoc(self):
        content = [Plain(self.text.to_pandoc())]
        children = super().to_pandoc()
        if children:
            content.extend(children)
        return content


class NumberedList(Block):
    def __init__(self, client: Client, block, get_children=True):
        self.client = client
        self.has_children = False
        self.items = []
        self.created_time = None
        self.last_edited_time = None
        self.type = "numbered_list"
        self.id = None

    def append(self, item: NumberedListItem):
        self.items.append(item)

    def to_pandoc(self):
        return OrderedList((1, Decimal(), Period()), [i.to_pandoc() for i in self.items])


class HeadingBase(Block):
    def __init__(self, client: Client, block, get_children=True):
        super().__init__(client, block, get_children)
        self.text = RichTextArray(self.text)

    def to_pandoc(self):
        return Header(self.level, ('', [], []), self.text.to_pandoc())


class HeadingOne(HeadingBase):
    level = 1


class HeadingTwo(HeadingBase):
    level = 2


class HeadingThree(HeadingBase):
    level = 3


class Divider(Block):
    def to_pandoc(self):
        return HorizontalRule()


class Bookmark(Block):
    def to_pandoc(self):
        caption = None
        if self.caption:
            caption = RichTextArray(self.caption).to_pandoc()
        else:
            caption = [Str(self.url)]
        return Para([Link(('', [], []), caption, (self.url, ''))])


class CodeBlockFenced(Block):
    def to_pandoc(self):
        return CodeBlock(('', [self.language], []), self.text[0]['plain_text'])


class Quote(Block):
    def to_pandoc(self):
        return BlockQuote([Para(RichTextArray(self.text).to_pandoc())])


class ImageBlock(Block):
    def __init__(self, client: Client, block, get_children=True):
        super().__init__(client, block, get_children)
        self.file = File(block['image'])

    def to_pandoc(self):
        url = None
        if self.file.type == "external":
            url = self.file.url
        elif self.file.type == "file":
            url = self.file.download()
        caption = RichTextArray(self.caption)
        return Para([Image(('', [], []), caption.to_pandoc(), (url, ''))])


class File():
    def __init__(self, obj):
        if obj['type'] == "file":
            self.type = "file"
            self.url = obj['file']['url']
            self.expiry_time = obj['file']['expiry_time']
        elif obj['type'] == "external":
            self.type = "external"
            self.url = obj['external']['url']

    def download(self):
        # TODO: append created time as hex to end of file to prevent collisions?
        if IMAGE_PATH and not path.exists(IMAGE_PATH):
            makedirs(IMAGE_PATH)
        parsed_url = urlparse(self.url)
        if IMAGE_PATH:
            local_filename = path.join(IMAGE_PATH, path.basename(parsed_url.path))
        else:
            local_filename = path.basename(parsed_url.path)
        with requests.get(self.url, stream=True) as request_stream:
            with open(local_filename, 'wb') as file_stream:
                copyfileobj(request_stream.raw, file_stream)
                if IMAGE_WEB_PATH:
                    return IMAGE_WEB_PATH + path.basename(parsed_url.path)
                else:
                    return path.basename(parsed_url.path)


class TableBlock(Block):
    def to_pandoc(self):
        children = super().to_pandoc()
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
        table = Table(('', [], []),  # attr
                      Caption(None, []),  # caption
                      colspec,
                      TableHead(('', [], []), header_rows),  # table header
                      [TableBody(('', [], []), RowHeadColumns(
                          row_header_columns), [], children)],   # table body
                      TableFoot(('', [], []), []))  # table footer
        return table


class RowBlock(Block):
    def to_pandoc(self):
        cells = [Cell(('', [], []),
                      AlignDefault(),
                      RowSpan(1),
                      ColSpan(1),
                      [Plain(RichTextArray(cell).to_pandoc())]) for cell in self.cells]
        row = Row(('', [], []), cells)
        return row


class Toggle(Block):
    # default implementation generates a bulleted list item with indented children
    # a plugin may be used to add html classes and replicate the interactive behavior
    def to_pandoc(self):
        header = RichTextArray(self.text).to_pandoc()
        children = super().to_pandoc()
        content = [Para(header)]
        content.extend(children)
        output = BulletList([content])
        return output

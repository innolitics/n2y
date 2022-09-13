from itertools import groupby
import logging
from urllib.parse import urljoin

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

    def __init__(self, client, notion_data, page=None, get_children=True):
        """
        The Notion client object is passed down for the following reasons:
        1. Some child objects may be unknown until the block is processed.
           Links to other Notion pages are an example.
        2. In some cases a block may choose not to get child blocks.
           Currently, all blocks load all children.
        """
        logger.debug('Instantiating "%s" block', type(self).__name__)
        self.client = client
        self.page = page

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
                children = self.client.get_child_blocks(self.notion_id, page, get_children)
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
                for b in blocks:
                    result = b.to_pandoc()
                    if isinstance(result, list):
                        # a few blocks return lists of nodes
                        pandoc_ast.extend(result)
                    elif result is not None:
                        # a plugin may decide to return None to indicate the
                        # block should be removed; ideally pandoc.types.Nil
                        # would handle this, but it doesn't appear to work
                        pandoc_ast.append(result)
        return pandoc_ast

    @property
    def notion_url(self):
        # the notion URL's don't work if the dashes from the block ID are present
        fragment = '#' + self.notion_id.replace('-', '')
        if self.page is None:
            return fragment
        else:
            return urljoin(self.page.notion_url, fragment)


class ListItemBlock(Block):
    @classmethod
    def list_to_pandoc(klass, items):
        raise NotImplementedError()


class ChildPageBlock(Block):
    def __init__(self, client, notion_data, page, get_children=True):
        super().__init__(client, notion_data, page, get_children)
        self.title = self.notion_data["title"]

    def to_pandoc(self):
        assert self.children is not None
        if self.children:
            children = self.children_to_pandoc()
            return Pandoc(Meta({'title': MetaString(self.title)}), children)
        else:
            return None


class EquationBlock(Block):
    def __init__(self, client, notion_data, page, get_children=True):
        super().__init__(client, notion_data, page, get_children)
        self.expression = self.notion_data["expression"]

    def to_pandoc(self):
        return Para([Math(DisplayMath(), self.expression)])


class ParagraphBlock(Block):
    def __init__(self, client, notion_data, page, get_children=True):
        super().__init__(client, notion_data, page, get_children)
        self.rich_text = client.wrap_notion_rich_text_array(self.notion_data["rich_text"], self)

    def to_pandoc(self):
        content = self.rich_text.to_pandoc()
        if self.has_children:
            # Notion allows you to create child blocks for a paragraph; these
            # child blocks appear indented relative to the paragraph. There's
            # no way to represent this indentation in pandoc's AST, so we just
            # append the child blocks afterwards.
            result = [Para(content)]
            children = self.children_to_pandoc()
            result.extend(children)
        else:
            result = Para(content)
        return result


class BulletedListItemBlock(ListItemBlock):
    def __init__(self, client, notion_data, page, get_children=True):
        super().__init__(client, notion_data, page, get_children)
        self.rich_text = client.wrap_notion_rich_text_array(self.notion_data["rich_text"], self)

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
    def __init__(self, client, notion_data, page, get_children=True):
        super().__init__(client, notion_data, page, get_children)
        self.checked = self.notion_data['checked']

        # TODO: Move this into the "to_pandoc" stage
        box = '☒ ' if self.checked else '☐ '
        self.rich_text.prepend(box)


class NumberedListItemBlock(ListItemBlock):
    def __init__(self, client, notion_data, page, get_children=True):
        super().__init__(client, notion_data, page, get_children)
        self.rich_text = client.wrap_notion_rich_text_array(self.notion_data["rich_text"], self)

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
    def __init__(self, client, notion_data, page, get_children=True):
        super().__init__(client, notion_data, page, get_children)
        self.rich_text = client.wrap_notion_rich_text_array(self.notion_data["rich_text"], self)

        # The Notion UI allows one to bold the text in a header, but the bold
        # styling isn't displayed. Thus, to avoid unexpected appearances of
        # bold text in the generated documents, bolding is removed.
        for rich_text in self.rich_text:
            rich_text.bold = False

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
    def __init__(self, client, notion_data, page, get_children=True):
        super().__init__(client, notion_data, page, get_children)
        self.url = self.notion_data["url"]
        self.caption = client.wrap_notion_rich_text_array(self.notion_data["caption"], self)

    def to_pandoc(self):
        if self.caption:
            caption_ast = self.caption.to_pandoc()
        else:
            caption_ast = [Str(self.url)]
        return Para([Link(('', [], []), caption_ast, (self.url, ''))])


class FencedCodeBlock(Block):
    pandoc_highlight_languages = [
        "abc", "actionscript", "ada", "agda", "apache", "asn1", "asp", "ats", "awk",
        "bash", "bibtex", "boo", "c", "changelog", "clojure", "cmake", "coffee",
        "coldfusion", "comments", "commonlisp", "cpp", "cs", "css", "curry", "d",
        "default", "diff", "djangotemplate", "dockerfile", "dot", "doxygen",
        "doxygenlua", "dtd", "eiffel", "elixir", "elm", "email", "erlang", "fasm",
        "fortranfixed", "fortranfree", "fsharp", "gcc", "glsl", "gnuassembler", "go",
        "graphql", "groovy", "hamlet", "haskell", "haxe", "html", "idris", "ini",
        "isocpp", "j", "java", "javadoc", "javascript", "javascriptreact", "json",
        "jsp", "julia", "kotlin", "latex", "lex", "lilypond", "literatecurry",
        "literatehaskell", "llvm", "lua", "m4", "makefile", "mandoc", "markdown",
        "mathematica", "matlab", "maxima", "mediawiki", "metafont", "mips", "modelines",
        "modula2", "modula3", "monobasic", "mustache", "nasm", "nim", "noweb",
        "objectivec", "objectivecpp", "ocaml", "octave", "opencl", "orgmode", "pascal",
        "perl", "php", "pike", "postscript", "povray", "powershell", "prolog",
        "protobuf", "pure", "purebasic", "python", "qml", "r", "raku", "relaxng",
        "relaxngcompact", "rest", "rhtml", "roff", "ruby", "rust", "sass", "scala",
        "scheme", "sci", "scss", "sed", "sgml", "sml", "spdxcomments", "sql",
        "sqlmysql", "sqlpostgresql", "stan", "stata", "swift", "systemverilog", "tcl",
        "tcsh", "texinfo", "toml", "typescript", "verilog", "vhdl", "xml", "xorg",
        "xslt", "xul", "yacc", "yaml", "zsh",
    ]

    # TODO: finish filling in this mapping from Notion language names to
    # pandoc's supported language names
    notion_to_pandoc_highlight_languages = {
        'c#': 'cs',
        'c++': 'cpp',
        'f#': 'fsharp',
        'objective-c': 'objectivec',
        'docker': 'dockerfile',
        'coffee': 'coffeescript',
        'shell': 'bash',  # seems better than nothing
    }

    def __init__(self, client, notion_data, page, get_children=True):
        super().__init__(client, notion_data, page, get_children)
        self.language = self.notion_data["language"]
        self.rich_text = client.wrap_notion_rich_text_array(self.notion_data["rich_text"], self)
        self.caption = client.wrap_notion_rich_text_array(self.notion_data["caption"], self)

    def to_pandoc(self):
        pandoc_language = self.notion_to_pandoc_highlight_languages.get(
            self.language, self.language,
        )
        if pandoc_language not in self.pandoc_highlight_languages:
            if pandoc_language != "plain text":
                msg = 'Dropping syntax highlighting for unsupported language "%s" (%s)'
                logger.warning(msg, pandoc_language, self.notion_url)
            language = []
        else:
            language = [pandoc_language]
        return CodeBlock(('', language, []), self.rich_text.to_plain_text())


class QuoteBlock(ParagraphBlock):
    def __init__(self, client, notion_data, page, get_children=True):
        super().__init__(client, notion_data, page, get_children)
        self.rich_text = client.wrap_notion_rich_text_array(self.notion_data["rich_text"], self)

    def to_pandoc(self):
        pandoc_ast = super().to_pandoc()
        return (
            BlockQuote(pandoc_ast)
            if isinstance(pandoc_ast, list)
            else BlockQuote([pandoc_ast])
        )


class FileBlock(Block):
    def __init__(self, client, notion_data, page, get_children=True):
        super().__init__(client, notion_data, page, get_children)
        self.file = client.wrap_notion_file(notion_data['file'])
        self.caption = client.wrap_notion_rich_text_array(self.notion_data["caption"], self)

    def to_pandoc(self):
        url = None
        if self.file.type == "external":
            url = self.file.url
        elif self.file.type == "file":
            url = self.client.download_file(self.file.url, self.page)
        content_ast = [Link(('', [], []), [Str(url)], (url, ''))]
        if self.caption:
            caption_ast = self.caption.to_pandoc()
            return render_with_caption(content_ast, caption_ast)
        return Para(content_ast)


class ImageBlock(Block):
    def __init__(self, client, notion_data, page, get_children=True):
        super().__init__(client, notion_data, page, get_children)
        self.file = client.wrap_notion_file(notion_data['image'])
        self.caption = client.wrap_notion_rich_text_array(self.notion_data["caption"], self)

    def to_pandoc(self):
        url = None
        if self.file.type == "external":
            url = self.file.url
        elif self.file.type == "file":
            url = self.client.download_file(self.file.url, self.page)
        img_alt = [Str(url)]
        if self.caption:
            img_alt = self.caption.to_pandoc()
        return Para([Image(('', [], []), img_alt, (url, ''))])


class TableBlock(Block):
    def __init__(self, client, notion_data, page, get_children=True):
        super().__init__(client, notion_data, page, get_children)
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
    def __init__(self, client, notion_data, page, get_children=True):
        super().__init__(client, notion_data, page, get_children)
        self.cells = [
            client.wrap_notion_rich_text_array(nc, self)
            for nc in self.notion_data["cells"]
        ]

    def to_pandoc(self):
        cells = [Cell(
            ('', [], []),
            AlignDefault(),
            RowSpan(1),
            ColSpan(1),
            [Plain(cell.to_pandoc())]
        ) for cell in self.cells]
        return Row(('', [], []), cells)


class ColumnListBlock(Block):
    def __init__(self, client, notion_data, page, get_children=True):
        super().__init__(client, notion_data, page, get_children)

    def to_pandoc(self):
        cells = []
        if self.children:
            cells = self.children_to_pandoc()
        colspec = [(AlignDefault(), ColWidthDefault()) for _ in range(len(cells))]
        table = Table(
            ('', [], []),
            Caption(None, []),
            colspec,
            TableHead(('', [], []), []),
            [TableBody(
                ('', [], []),
                RowHeadColumns(0), [],
                [Row(('', [], []), cells)])],
            TableFoot(('', [], []), [])
        )
        return table


class ColumnBlock(Block):
    def to_pandoc(self):
        return Cell(
            ('', [], []),
            AlignDefault(),
            RowSpan(1),
            ColSpan(1),
            self.children_to_pandoc()
        )


class ToggleBlock(Block):
    """
    Generates a bulleted list item with indented children. A plugin may be used
    to add html classes and replicate the interactive behavior found in Notion.
    """

    def __init__(self, client, notion_data, page, get_children=True):
        super().__init__(client, notion_data, page, get_children)
        self.rich_text = client.wrap_notion_rich_text_array(self.notion_data["rich_text"], self)

    def to_pandoc(self):
        header = self.rich_text.to_pandoc()
        children = self.children_to_pandoc()
        content = [Para(header)]
        content.extend(children)
        return BulletList([content])


class CalloutBlock(Block):
    def __init__(self, client, notion_data, page, get_children=True):
        super().__init__(client, notion_data, page, get_children)
        self.rich_text = client.wrap_notion_rich_text_array(self.notion_data["rich_text"], self)
        # the color and icon are not currently used

    def to_pandoc(self):
        content = self.rich_text.to_pandoc()
        if self.has_children:
            children = self.children_to_pandoc()
            result = [Para(content)]
            result.extend(children)
        else:
            result = Para(content)
        return result


class NoopBlock(Block):
    def __init__(self, client, notion_data, page, get_children=True):
        # don't get the child blocks, as we're not using the data
        super().__init__(client, notion_data, page, get_children=False)

    def to_pandoc(self):
        return None


class TableOfContentsBlock(NoopBlock):
    pass


class BreadcrumbBlock(NoopBlock):
    pass


class UnsupportedBlock(NoopBlock):
    pass


class TemplateBlock(NoopBlock):
    pass


class WarningBlock(NoopBlock):
    def to_pandoc(self):
        logger.warning('Skipping unsupported "%s" block (%s)', self.notion_type, self.notion_url)
        return None


class ChildDatabaseBlock(WarningBlock):
    pass


class EmbedBlock(WarningBlock):
    pass


class VideoBlock(Block):
    def __init__(self, client, notion_data, page, get_children=True):
        super().__init__(client, notion_data, page, get_children)
        self.file = client.wrap_notion_file(notion_data['video'])
        self.caption = client.wrap_notion_rich_text_array(self.notion_data["caption"], self)

    def to_pandoc(self):
        url = None
        if self.file.type == "external":
            url = self.file.url
        elif self.file.type == "file":
            url = self.client.download_file(self.file.url, self.page)
        content_ast = [Link(('', [], []), [Str(url)], (url, ''))]
        if self.caption:
            caption_ast = self.caption.to_pandoc()
            return render_with_caption(content_ast, caption_ast)
        return Para(content_ast)


class PdfBlock(WarningBlock):
    def __init__(self, client, notion_data, page, get_children=True):
        super().__init__(client, notion_data, page, get_children)
        self.pdf = client.wrap_notion_file(notion_data['pdf'])
        self.caption = client.wrap_notion_rich_text_array(self.notion_data["caption"], self)

    def to_pandoc(self):
        url = self.client.download_file(self.pdf.url, self.page)
        content_ast = [Link(('', [], []), [Str(url)], (url, ''))]
        if self.caption:
            caption_ast = self.caption.to_pandoc()
            return render_with_caption(content_ast, caption_ast)
        return Para(content_ast)


class ChildrenPassThroughBlock(Block):
    """
    Just passes along the children of the block.
    """

    def to_pandoc(self):
        return self.children_to_pandoc()


class LinkPreviewBlock(WarningBlock):
    pass


class SyncedBlock(Block):
    def __init__(self, client, notion_data, page, get_children=True):
        self.original = notion_data[notion_data["type"]]["synced_from"] is None
        super().__init__(client, notion_data, page, get_children=self.original)
        # Synced blocks will always have children unless not shared
        # (There will always be at least one UnsupportedBlock child)
        self.shared = self.has_children
        self.children = self._get_synced_block_children()

    def _get_synced_block_children(self):
        if not self.original and self.shared:
            return self.client.get_child_blocks(
                self.notion_data["synced_from"]["block_id"],
                self.page, True,
            )
        return self.children

    def to_pandoc(self):
        if not self.shared:
            logger.warning('Skipping un-shared synced block (%s)', self.notion_url)
            return None
        return self.children_to_pandoc()


class LinkToPageBlock(Block):
    def __init__(self, client, notion_data, page, get_children=True):
        super().__init__(client, notion_data, page, get_children)

        self.link_type = self.notion_data["type"]
        # The key for the object id may be either "page_id"
        # or "database_id".
        self.linked_page_id = self.notion_data[self.link_type]

    def to_pandoc(self):
        # TODO: in the future, if we are exporting the linked page too, then add
        # a link to the page. For now, we just display the text of the page.

        page = self.client.get_page_or_database(self.linked_page_id)
        if page is None:
            msg = "Permission denied when attempting to access linked page [%s]"
            logger.warning(msg, self.notion_url)
            return None
        else:
            title = page.title.to_pandoc()
            return Para(title)


def render_with_caption(content_ast, caption_ast):
    header_cell_args = [('', [], []), AlignDefault(), RowSpan(1), ColSpan(1), [Plain(content_ast)]]
    body_cell_args = [('', [], []), AlignDefault(), RowSpan(1), ColSpan(1), [Plain(caption_ast)]]
    body_row = Row(('', [], []), [Cell(*body_cell_args)])
    return Table(
        ('', [], []),
        Caption(None, []),
        [(AlignDefault(), ColWidthDefault())],
        TableHead(('', [], []), [Row(('', [], []), [Cell(*header_cell_args)])]),
        [TableBody(('', [], []), RowHeadColumns(0), [], [body_row])],
        TableFoot(('', [], []), [])
    )


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
    "child_database": ChildDatabaseBlock,
    "embed": EmbedBlock,
    "image": ImageBlock,
    "video": VideoBlock,
    "file": FileBlock,
    "pdf": PdfBlock,
    "bookmark": BookmarkBlock,
    "callout": CalloutBlock,
    "quote": QuoteBlock,
    "equation": EquationBlock,
    "divider": DividerBlock,
    "table_of_contents": TableOfContentsBlock,
    "breadcrumb": TableOfContentsBlock,
    "column": ColumnBlock,
    "column_list": ColumnListBlock,
    "link_preview": LinkPreviewBlock,
    "synced_block": SyncedBlock,
    "template": TemplateBlock,
    "link_to_page": LinkToPageBlock,
    "code": FencedCodeBlock,
    "table": TableBlock,
    "table_row": RowBlock,
    "unsupported": UnsupportedBlock,
}

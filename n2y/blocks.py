from itertools import groupby
from re import match
from urllib.parse import urljoin

from pandoc.types import (
    AlignDefault,
    BlockQuote,
    BulletList,
    Caption,
    Cell,
    CodeBlock,
    ColSpan,
    ColWidthDefault,
    Decimal,
    DisplayMath,
    Header,
    HorizontalRule,
    Image,
    Link,
    Math,
    OrderedList,
    Pandoc,
    Para,
    Period,
    Plain,
    Row,
    RowHeadColumns,
    RowSpan,
    Str,
    Table,
    TableBody,
    TableFoot,
    TableHead,
)

from n2y.notion_mocks import mock_block, mock_rich_text_array
from n2y.utils import header_id_from_text, pandoc_write_or_log_errors, yaml_map_to_meta


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
        client.logger.debug('Instantiating "%s" block', type(self).__name__)
        self.client = client
        self.page = page

        self.notion_id = notion_data["id"]
        self.created_time = notion_data["created_time"]
        self.created_by = notion_data["created_by"]
        self.last_edited_time = notion_data["last_edited_time"]
        self.last_edited_by = notion_data["last_edited_by"]
        self.has_children = notion_data["has_children"]
        self.archived = notion_data["archived"]
        self.notion_type = notion_data["type"]
        self.notion_data = notion_data
        if get_children:
            self.get_children()
        else:
            self.children = None

    def get_children(self):
        if self.has_children:
            self.children = self.client.get_child_blocks(self.notion_id, self.page, True)
        else:
            self.children = []

    def to_pandoc(self):
        raise NotImplementedError()

    def children_to_pandoc(self):
        pandoc_ast = []
        for block_type, blocks in groupby(self.children, lambda c: type(c)):
            if issubclass(block_type, ListItemBlock):
                pandoc_ast.append(block_type.list_to_pandoc(blocks))
            else:
                for b in blocks:
                    result = b.to_pandoc()
                    if block_type == ChildPageBlock:
                        pandoc_ast.extend(result[1])
                    elif isinstance(result, list):
                        # a few blocks return lists of nodes
                        pandoc_ast.extend(result)
                    elif result is not None:
                        # a plugin may decide to return None to indicate the
                        # block should be removed; ideally pandoc.types.Nil
                        # would handle this, but it doesn't appear to work
                        pandoc_ast.append(result)
        return pandoc_ast

    @property
    def notion_type_data(self):
        return self.notion_data[self.notion_data["type"]]

    @property
    def notion_url(self):
        # the notion URL's don't work if the dashes from the block ID are present
        fragment = "#" + self.notion_id.replace("-", "")
        if self.page is None:
            return fragment
        else:
            return urljoin(self.page.notion_url, fragment)


class ListItemBlock(Block):
    @classmethod
    def list_to_pandoc(cls, items):
        raise NotImplementedError()


class ChildPageBlock(Block):
    def __init__(self, client, notion_data, page, get_children=True):
        super().__init__(client, notion_data, page, get_children)
        self.title = self.notion_type_data["title"]

    def to_pandoc(self):
        assert self.children is not None
        children = self.children_to_pandoc()
        if self.page:
            properties = self.page.properties_to_values()
        else:
            properties = {}
        meta = yaml_map_to_meta(properties)
        return Pandoc(meta, children)


class EquationBlock(Block):
    def __init__(self, client, notion_data, page, get_children=True):
        super().__init__(client, notion_data, page, get_children)
        self.expression = self.notion_type_data["expression"]

    def to_pandoc(self):
        return Para([Math(DisplayMath(), self.expression)])


class ParagraphBlock(Block):
    def __init__(self, client, notion_data, page, get_children=True):
        super().__init__(client, notion_data, page, get_children)
        self.rich_text = client.wrap_notion_rich_text_array(
            self.notion_type_data["rich_text"], self
        )

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
        self.rich_text = client.wrap_notion_rich_text_array(
            self.notion_type_data["rich_text"], self
        )

    def to_pandoc(self):
        content = [Plain(self.rich_text.to_pandoc())]
        if self.has_children:
            children = self.children_to_pandoc()
            for child in children:
                if isinstance(child, Table):
                    # A bug in pandoc's markdown reader makes it unable to register mid-list tables.
                    # This adds an extra space between the table and the previous list item, which
                    # Allows the table to be read as such.
                    content.append(Para([]))
                content.append(child)
        return content

    @classmethod
    def list_to_pandoc(cls, items):
        return BulletList([b.to_pandoc() for b in items])


class ToDoListItemBlock(BulletedListItemBlock):
    def __init__(self, client, notion_data, page, get_children=True):
        super().__init__(client, notion_data, page, get_children)
        self.checked = self.notion_type_data["checked"]

        box = "☒ " if self.checked else "☐ "
        self.rich_text.prepend(box)


class NumberedListItemBlock(BulletedListItemBlock):
    @classmethod
    def list_to_pandoc(cls, items):
        return OrderedList((1, Decimal(), Period()), [b.to_pandoc() for b in items])


class TableOfContentsBlock(Block):
    def __init__(self, client, notion_data, page, get_children=True):
        self.subheaders: list[Header] | None = notion_data[notion_data["type"]].get(
            "subheaders", None
        )
        super().__init__(client, notion_data, page, get_children)

    def get_children(self):
        if self.subheaders is not None:
            children: list[TableOfContentsItemBlock] = []
            subsections: list[list[Header]] = []
            # Sometimes, the first header is not an H1, so we need to find the first
            base: int = self.subheaders[0][0]
            index: int = -1
            for header in self.subheaders:
                if header[0] == base:
                    index += 1
                    subsections.append([header])
                if header[0] > base:
                    subsections[index].append(header)
                if header[0] < base:
                    self.client.logger.warning(
                        f'Skipping out-of-order header "{header[1][0]}" in table of'
                        " contents for page named"
                        f" {self.page.title.to_plain_text()} ({self.page.notion_url})."
                        " The base header is an H{base} so all following headers"
                        " should be H{base} or greater."
                    )
            for subsection in subsections:
                notion_data = self.generate_item_block(subsection)
                children.append(
                    TableOfContentsItemBlock(self.client, notion_data, self.page)
                )
            if children:
                self.has_children = True
            self.children = children
        else:
            self.children = None

    def get_subheaders(self, ast_list):
        self.subheaders: list[Header] | None = []
        for block in ast_list:
            if isinstance(block, Header):
                self.subheaders.append(block)

    def to_pandoc(self):
        if not self.children:
            return None
        else:
            return self.children_to_pandoc()

    def generate_item_block(self, section: list[Header]):
        header = section.pop(0)
        header_text = pandoc_write_or_log_errors(
            header[2], "plain", [], self.client.logger
        )[:-1]
        rich_text = mock_rich_text_array([(header_text, None, f"#{header[1][0]}")])
        type_data = {
            "header": header,
            "subheaders": section,
            "rich_text": rich_text,
        }
        return mock_block("table_of_contents_item", type_data)

    def render_toc(self, ast_list):
        self.get_subheaders(ast_list)
        self.get_children()


class TableOfContentsItemBlock(NumberedListItemBlock, TableOfContentsBlock):
    def __init__(self, client, notion_data, page, get_children=True):
        type_data = notion_data[notion_data["type"]]
        self.header = type_data["header"]
        self.level = self.header[0]
        super().__init__(client, notion_data, page, get_children)

    def get_children(self):
        children: list[TableOfContentsItemBlock] = []
        subsections: list[list[Header]] = []
        index: int = -1
        for header in self.subheaders:
            if header[0] == self.level + 1:
                index += 1
                subsections.append([header])
            if header[0] > self.level + 1:
                try:
                    subsections[index].append(header)
                except IndexError:
                    self.client.logger.warning(
                        f'Skipping out-of-order header "{header[1][0]}" in table of'
                        " contents for page named"
                        f" {self.page.title.to_plain_text()} ({self.page.notion_url})."
                        " Please create headers in sequence (i.e. proper document"
                        f" formatting dictates that an H{self.level} should not be"
                        f" immediately followed by an H{header[0]}, but an"
                        f" H{self.level + 1})."
                    )
        for subsection in subsections:
            notion_data = self.generate_item_block(subsection)
            children.append(TableOfContentsItemBlock(self.client, notion_data, self.page))
        if children:
            self.has_children = True
        self.children = children


class HeadingBlock(Block):
    def __init__(self, client, notion_data, page, get_children=True):
        super().__init__(client, notion_data, page, get_children)
        self.rich_text = client.wrap_notion_rich_text_array(
            self.notion_type_data["rich_text"], self
        )

        # The Notion UI allows one to bold the text in a header, but the bold
        # styling isn't displayed. Thus, to avoid unexpected appearances of
        # bold text in the generated documents, bolding is removed.
        for rich_text in self.rich_text:
            rich_text.bold = False

    def to_pandoc(self):
        section_id = header_id_from_text(self.rich_text.to_plain_text())
        return Header(self.level, (section_id, [], []), self.rich_text.to_pandoc())


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
        self.url = self.notion_type_data["url"]
        self.caption = client.wrap_notion_rich_text_array(
            self.notion_type_data["caption"], self
        )

    def to_pandoc(self):
        if self.caption:
            caption_ast = self.caption.to_pandoc()
        else:
            caption_ast = [Str(self.url)]
        return Para([Link(("", [], []), caption_ast, (self.url, ""))])


class FencedCodeBlock(Block):
    pandoc_highlight_languages = [
        "abc",
        "actionscript",
        "ada",
        "agda",
        "apache",
        "asn1",
        "asp",
        "ats",
        "awk",
        "bash",
        "bibtex",
        "boo",
        "c",
        "changelog",
        "clojure",
        "cmake",
        "coffee",
        "coldfusion",
        "comments",
        "commonlisp",
        "cpp",
        "cs",
        "css",
        "curry",
        "d",
        "default",
        "diff",
        "djangotemplate",
        "dockerfile",
        "dot",
        "doxygen",
        "doxygenlua",
        "dtd",
        "eiffel",
        "elixir",
        "elm",
        "email",
        "erlang",
        "fasm",
        "fortranfixed",
        "fortranfree",
        "fsharp",
        "gcc",
        "glsl",
        "gnuassembler",
        "go",
        "graphql",
        "groovy",
        "hamlet",
        "haskell",
        "haxe",
        "html",
        "idris",
        "ini",
        "isocpp",
        "j",
        "java",
        "javadoc",
        "javascript",
        "javascriptreact",
        "json",
        "jsp",
        "julia",
        "kotlin",
        "latex",
        "lex",
        "lilypond",
        "literatecurry",
        "literatehaskell",
        "llvm",
        "lua",
        "m4",
        "makefile",
        "mandoc",
        "markdown",
        "mathematica",
        "matlab",
        "maxima",
        "mediawiki",
        "metafont",
        "mips",
        "modelines",
        "modula2",
        "modula3",
        "monobasic",
        "mustache",
        "nasm",
        "nim",
        "noweb",
        "objectivec",
        "objectivecpp",
        "ocaml",
        "octave",
        "opencl",
        "orgmode",
        "pascal",
        "perl",
        "php",
        "pike",
        "postscript",
        "povray",
        "powershell",
        "prolog",
        "protobuf",
        "pure",
        "purebasic",
        "python",
        "qml",
        "r",
        "raku",
        "relaxng",
        "relaxngcompact",
        "rest",
        "rhtml",
        "roff",
        "ruby",
        "rust",
        "sass",
        "scala",
        "scheme",
        "sci",
        "scss",
        "sed",
        "sgml",
        "sml",
        "spdxcomments",
        "sql",
        "sqlmysql",
        "sqlpostgresql",
        "stan",
        "stata",
        "swift",
        "systemverilog",
        "tcl",
        "tcsh",
        "texinfo",
        "toml",
        "typescript",
        "verilog",
        "vhdl",
        "xml",
        "xorg",
        "xslt",
        "xul",
        "yacc",
        "yaml",
        "zsh",
    ]

    # TODO: finish filling in this mapping from Notion language names to
    # pandoc's supported language names
    notion_to_pandoc_highlight_languages = {
        "c#": "cs",
        "c++": "cpp",
        "f#": "fsharp",
        "objective-c": "objectivec",
        "docker": "dockerfile",
        "coffee": "coffeescript",
        "shell": "bash",  # seems better than nothing
    }

    def __init__(self, client, notion_data, page, get_children=True):
        super().__init__(client, notion_data, page, get_children)
        self.language = self.notion_type_data["language"]
        self.rich_text = client.wrap_notion_rich_text_array(
            self.notion_type_data["rich_text"], self
        )
        self.caption = client.wrap_notion_rich_text_array(
            self.notion_type_data["caption"], self
        )

    def to_pandoc(self):
        pandoc_language = self.notion_to_pandoc_highlight_languages.get(
            self.language,
            self.language,
        )
        if pandoc_language not in self.pandoc_highlight_languages:
            if pandoc_language != "plain text":
                msg = 'Dropping syntax highlighting for unsupported language "%s" (%s)'
                self.client.logger.warning(msg, pandoc_language, self.notion_url)
            language = []
        else:
            language = [pandoc_language]
        return CodeBlock(("", language, []), self.rich_text.to_plain_text())


class QuoteBlock(ParagraphBlock):
    def __init__(self, client, notion_data, page, get_children=True):
        super().__init__(client, notion_data, page, get_children)
        self.rich_text = client.wrap_notion_rich_text_array(
            self.notion_type_data["rich_text"], self
        )

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
        self.file = client.wrap_notion_file(notion_data["file"])
        self.caption = client.wrap_notion_rich_text_array(
            self.notion_type_data["caption"], self
        )
        potential_name = match(
            (
                r".+(?:[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/)+"
                r"(?P<name>.+)\?.+"
            ),
            self.file.url,
        )
        name = potential_name.groups("name") if potential_name else None
        self.name = name[0] if name else None

    def to_pandoc(self):
        url = None
        if self.file.type == "external":
            url = self.file.url
        elif self.file.type == "file":
            url = self.client.download_file(self.file.url, self.page, self.notion_id)
        content_ast = [Link(("", [], []), [Str(self.name or url)], (url, ""))]
        if self.caption:
            caption_ast = self.caption.to_pandoc()
            return render_with_caption(content_ast, caption_ast)
        return Para(content_ast)


class ImageBlock(Block):
    def __init__(self, client, notion_data, page, get_children=True):
        super().__init__(client, notion_data, page, get_children)
        self.file = client.wrap_notion_file(notion_data["image"])
        self.caption = client.wrap_notion_rich_text_array(
            self.notion_type_data["caption"], self
        )

    def to_pandoc(self):
        url = None
        if self.file.type == "external":
            url = self.file.url
        elif self.file.type == "file":
            url = self.client.download_file(self.file.url, self.page, self.notion_id)
        caption = []
        fig_flag = ""
        if self.caption:
            fig_flag = "fig:"
            caption = self.caption.to_pandoc()
        return Para([Image(("", [], []), caption, (url, fig_flag))])


class TableBlock(Block):
    def __init__(self, client, notion_data, page, get_children=True):
        super().__init__(client, notion_data, page, get_children)
        self.has_column_header = self.notion_type_data["has_column_header"]
        self.has_row_header = self.notion_type_data["has_row_header"]
        self.table_width = self.notion_type_data["table_width"]

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
            ("", [], []),
            Caption(None, []),
            colspec,
            TableHead(("", [], []), header_rows),
            [TableBody(("", [], []), RowHeadColumns(row_header_columns), [], children)],
            TableFoot(("", [], []), []),
        )
        return table


class RowBlock(Block):
    def __init__(self, client, notion_data, page, get_children=True):
        super().__init__(client, notion_data, page, get_children)
        self.cells = [
            client.wrap_notion_rich_text_array(nc, self)
            for nc in self.notion_type_data["cells"]
        ]

    def to_pandoc(self):
        cells = []
        for cell in self.cells:
            pandoc = cell.to_pandoc()
            cells.append(
                Cell(
                    ("", [], []),
                    AlignDefault(),
                    RowSpan(1),
                    ColSpan(1),
                    [Plain(pandoc)],
                )
            )
        return Row(("", [], []), cells)


class ColumnListBlock(Block):
    def __init__(self, client, notion_data, page, get_children=True):
        super().__init__(client, notion_data, page, get_children)

    def to_pandoc(self):
        pandoc = []
        if self.children:
            pandoc = self.children_to_pandoc()
        return pandoc


class ColumnBlock(Block):
    def to_pandoc(self):
        return self.children_to_pandoc()


class ToggleBlock(Block):
    """
    Generates a bulleted list item with indented children. A plugin may be used
    to add html classes and replicate the interactive behavior found in Notion.
    """

    def __init__(self, client, notion_data, page, get_children=True):
        super().__init__(client, notion_data, page, get_children)
        self.rich_text = client.wrap_notion_rich_text_array(
            self.notion_type_data["rich_text"], self
        )

    def to_pandoc(self):
        header = self.rich_text.to_pandoc()
        children = self.children_to_pandoc()
        content = [Para(header)]
        content.extend(children)
        return BulletList([content])


class CalloutBlock(Block):
    def __init__(self, client, notion_data, page, get_children=True):
        super().__init__(client, notion_data, page, get_children)
        self.rich_text = client.wrap_notion_rich_text_array(
            self.notion_type_data["rich_text"], self
        )
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


class BreadcrumbBlock(NoopBlock):
    pass


class UnsupportedBlock(NoopBlock):
    pass


class TemplateBlock(NoopBlock):
    pass


class WarningBlock(NoopBlock):
    def to_pandoc(self):
        self.client.logger.warning(
            'Skipping unsupported "%s" block (%s)', self.notion_type, self.notion_url
        )
        return None


class ChildDatabaseBlock(NoopBlock):
    pass


class EmbedBlock(WarningBlock):
    pass


class ContentBlock(Block):
    """
    Generic base class for blocks that contain file-based content that should be
    downloaded and then linked to.
    """

    def __init__(self, client, notion_data, page, get_children=True):
        super().__init__(client, notion_data, page, get_children)
        self.file = client.wrap_notion_file(self.notion_type_data)
        self.caption = client.wrap_notion_rich_text_array(
            self.notion_type_data["caption"], self
        )

    def to_pandoc(self):
        url = None
        if self.file.type == "external":
            url = self.file.url
        elif self.file.type == "file":
            url = self.client.download_file(self.file.url, self.page, self.notion_id)
        content_ast = [Link(("", [], []), [Str(url)], (url, ""))]
        if self.caption:
            caption_ast = self.caption.to_pandoc()
            return render_with_caption(content_ast, caption_ast)
        else:
            return Para(content_ast)


class AudioBlock(ContentBlock):
    pass


class VideoBlock(ContentBlock):
    pass


class PdfBlock(Block):
    def __init__(self, client, notion_data, page, get_children=True):
        super().__init__(client, notion_data, page, get_children)
        self.pdf = client.wrap_notion_file(notion_data["pdf"])
        self.caption = client.wrap_notion_rich_text_array(
            self.notion_type_data["caption"], self
        )

    def to_pandoc(self):
        url = self.client.download_file(self.pdf.url, self.page, self.notion_id)
        content_ast = [Link(("", [], []), [Str(url)], (url, ""))]
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
        self.is_recursive = None
        # Synced blocks will always have children unless not shared
        # (There will always be at least one UnsupportedBlock child)
        self.shared = self.has_children
        self.children = self._get_synced_block_children()

    def _get_synced_block_children(self):
        if not self.original and self.shared:
            # This last condition is to protect against recursive synced blocks while
            # still allowing synced blocks that are children of other synced blocks
            # (once Notion confirms that this bug has been addressed it can be removed)
            parent = self.notion_data.get("parent", None)
            self.is_recursive = (
                parent
                and self.notion_type_data["synced_from"]["block_id"]
                == parent[parent["type"]]
            )
            if not self.is_recursive:
                return self.client.get_child_blocks(
                    self.notion_type_data["synced_from"]["block_id"],
                    self.page,
                    True,
                )
        return self.children

    def to_pandoc(self):
        if not self.shared:
            # We can't reliably log a warning here because there is a bug in Notion that
            # causes too many disruptive false positives.
            return None
        elif self.is_recursive:
            self.client.logger.warning(
                "Skipping recursive synced block (%s)", self.notion_url
            )
            return None
        return self.children_to_pandoc()


class LinkToPageBlock(Block):
    def __init__(self, client, notion_data, page, get_children=True):
        super().__init__(client, notion_data, page, get_children)

        self.link_type = self.notion_type_data["type"]
        # The key for the object id may be either "page_id"
        # or "database_id".
        self.linked_node_id = self.notion_type_data[self.link_type]

    def to_pandoc(self):
        # TODO: in the future, if we are exporting the linked page too, then add
        # a link to the page. For now, we just display the text of the page.
        if self.link_type == "page_id":
            node = self.client.get_page(self.linked_node_id)
        elif self.link_type == "database_id":
            node = self.client.get_database(self.linked_node_id)
        else:
            raise NotImplementedError(f"Unknown link type: {self.link_type}")

        if node is None:
            msg = "Permission denied when attempting to access linked node (%r)"
            self.client.logger.warning(msg, self.notion_url)
            return None
        else:
            title = node.title.to_pandoc()
            return Para(title)


def render_with_caption(content_ast, caption_ast):
    header_cell_args = [
        ("", [], []),
        AlignDefault(),
        RowSpan(1),
        ColSpan(1),
        [Plain(content_ast)],
    ]
    body_cell_args = [
        ("", [], []),
        AlignDefault(),
        RowSpan(1),
        ColSpan(1),
        [Plain(caption_ast)],
    ]
    body_row = Row(("", [], []), [Cell(*body_cell_args)])
    return Table(
        ("", [], []),
        Caption(None, []),
        [(AlignDefault(), ColWidthDefault())],
        TableHead(("", [], []), [Row(("", [], []), [Cell(*header_cell_args)])]),
        [TableBody(("", [], []), RowHeadColumns(0), [], [body_row])],
        TableFoot(("", [], []), []),
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
    "audio": AudioBlock,
    "video": VideoBlock,
    "file": FileBlock,
    "pdf": PdfBlock,
    "bookmark": BookmarkBlock,
    "callout": CalloutBlock,
    "quote": QuoteBlock,
    "equation": EquationBlock,
    "divider": DividerBlock,
    "table_of_contents": TableOfContentsBlock,
    "table_of_contents_item": TableOfContentsItemBlock,
    "breadcrumb": BreadcrumbBlock,
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

import logging
from itertools import groupby
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

        self.notion_block = notion_data
        self.notion_id = notion_data['id']
        self.created_time = notion_data['created_time']
        self.created_by = notion_data['created_by']
        self.last_edited_time = notion_data['last_edited_time']
        self.last_edited_by = notion_data['last_edited_by']
        self.has_children = notion_data['has_children']
        self.archived = notion_data['archived']
        self.notion_type = notion_data['type']
        self.notion_data = notion_data[notion_data['type']]
        self.get_children = get_children

        if get_children and self.has_children:
            children = self.client.get_child_blocks(self.notion_id, page, get_children)
        else:
            children = Children(client=self.client)
        self.children = children

    def replicate(self):
        return self.client.wrap_notion_block(self.notion_block, self.page, self.get_children)

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


class ChildDatabaseBlock(NoopBlock):
    def to_pandoc(self):
        msg = (
            'Skipping unsupported "%s" block (%s). '
            'Perhaps you can convert the database into a simple table?'
        )
        logger.warning(msg, self.notion_type, self.notion_url)
        return None


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


class PdfBlock(Block):
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
        self.linked_node_id = self.notion_data[self.link_type]

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
            msg = "Permission denied when attempting to access linked node [%s]"
            logger.warning(msg, self.notion_url)
            return None
        else:
            title = node.title.to_pandoc()
            return Para(title)


class Children(list):
    def __init__(self, *args, client=None):
        super().__init__(*args)
        if not client:
            raise NotImplementedError('No client assigned')
        self.default_link_title = '{Not Accessable}'
        self._default_info()
        self.client = client

    @property
    def block_list(self):
        return [child.notion_block for child in self]

    def copy_to(self, destination, probe_links=True):
        self.destination = destination
        self._define_page()
        not probe_links or self._probe_destination_links()
        self._format_for_copy()
        self._copy_to_api()
        not probe_links or self._comment_warnings()
        self._recursively_copy_children()
        self._copy_to_destination()
        self._default_info()
        return self.destination

    def _copy_to_api(self):
        last_index = 0
        for i, node in enumerate(self.child_pages_or_databases):
            if node[1] != last_index:
                blocks = self.notion_children[last_index:node[1]]
                appension_return = self.client.append_block_children(
                    self.destination.notion_id, blocks
                )
                self.children_appended.extend(appension_return['results'])

            if node[0] == 'database':
                database = self.client.create_notion_database(self.notion_children[node[1]])
                self.children_appended.append(database)
            elif node[0] == 'page':
                page = self.client.create_notion_page(self.notion_children[node[1]])
                self.children_appended.append(page)

            last_index = node[1] + 1

            if i == len(self.child_pages_or_databases) - 1:
                blocks = self.notion_children[last_index:]
                appension_return = self.client.append_block_children(
                    self.destination.notion_id, blocks
                )
                self.children_appended.extend(appension_return['results'])

        if not self.child_pages_or_databases:
            appension_return = self.client.append_block_children(
                self.destination.notion_id, self.notion_children
            )
            self.children_appended = appension_return['results']

    def _new_child_data(self, child):
        if issubclass(type(child), Block):
            notion_type = child.notion_type
            self.child_data = {
                'object': 'block',
                'type': notion_type,
                'has_children': child.has_children,
                notion_type: {**child.notion_data}
            }
        elif isinstance(child, dict):
            self.child_data = child
        else:
            raise NotImplementedError(
                f'this process does not support children of the {type(child)} type)'
            )

    def _format_for_copy(self):
        for i, child in enumerate(self):
            self._generate_child_data(child, i)

    def _generate_child_data(self, child, i):
        notion_type = child.notion_type
        self._new_child_data(child)
        if notion_type == 'unsupported':
            self._raise_unsupported_block_warning()
            return
        if notion_type == 'synced_block' and self.child_data[notion_type]['synced_from']:
            self.child_data[notion_type]['synced_from'] = None
        elif notion_type == 'paragraph':
            self._audit_mentions(i)
        elif notion_type == 'link_to_page':
            self._audit_links(i)
        elif notion_type == 'pdf':
            self._audit_pdf(i)
        elif notion_type in ['image', 'file']:
            self._audit_file_or_image(i, notion_type)
        elif 'child_' in notion_type:
            raise NotImplementedError((
                'This functionality is not yet supported for the '
                f'block type {notion_type}.'
            ))
            # Child Databases and Child Pages are not currently supported
            # but the commented out code will help handle them in the future

            # self.child_data = self.client.get_notion_block(child.notion_id)
            # self.child_pages_or_databases.append(('database', i))
        if notion_type in ['table', 'column_list']:
            child.children._format_for_copy()
            self.child_data[notion_type]['children'] = child.children.notion_children
        elif notion_type == 'column':
            self._audit_column(child, i)
        elif child.children:
            self.child_dict[i] = child.children
        else:
            del self.child_data['has_children']
        self.notion_children.append(self.child_data)

    def _raise_unsupported_block_warning(self):
        logger.warning('skipping unsupported block in Children.copy_to()')
        warning = 'WARNING: Unsupported Block(s) Skipped'
        comments = [
            comment.rich_text.to_plain_text() for comment in
            self.client.get_comments(self.page.notion_id)
        ]
        warning in comments or self.client.create_notion_comment(
            self.page.notion_id, [(warning, ['color:red'])]
        )

    def _comment_warnings(self):
        page_url = self.page.notion_url
        page_id = self.page.notion_id
        link_text = self._format_link_comments(page_url)
        file_text = self._format_file_comments(page_url)
        image_text = self._format_image_comments(page_url)
        pdf_text = self._format_pdf_comments(page_url)
        if pdf_text:
            self.client.create_notion_comment(page_id, pdf_text)
        if image_text:
            self.client.create_notion_comment(page_id, image_text)
        if link_text:
            self.client.create_notion_comment(page_id, link_text)
        if file_text:
            self.client.create_notion_comment(page_id, file_text)

    def _format_link_comments(self, page_url):
        link_text = []
        for index, title in self.comment_dict['link']:
            node = self.children_appended[index]
            node_url = page_url + f'#{node["id"]}'.replace('-', '')
            if link_text == []:
                link_text.append(["Unaudited Links:\n"])
            link_text.extend([
                ['- '],
                (f'{title}\n',
                    None,
                    None,
                    None,
                    {'type': 'url', 'url': node_url})
            ])
        return link_text

    def _format_pdf_comments(self, page_url):
        pdf_text = []
        for i, (index, url) in enumerate(self.comment_dict['pdf'], 1):
            node = self.children_appended[index]
            node_url = page_url + f'#{node["id"]}'.replace('-', '')
            if pdf_text == []:
                pdf_text.append(["Unaudited PDFs:\n"])
            pdf_str = f'pdf_{i}'
            pdf_text.extend([
                ['- '],
                (f'{pdf_str}',
                    None,
                    None,
                    None,
                    {'type': 'url', 'url': node_url}),
                (f': {url}\n',
                    None,
                    url)
            ])
        return pdf_text

    def _format_file_comments(self, page_url):
        file_text = []
        for i, (index, url) in enumerate(self.comment_dict['file'], 1):
            node = self.children_appended[index]
            node_url = page_url + f'#{node["id"]}'.replace('-', '')
            if file_text == []:
                file_text.append(["Unaudited Files:\n"])
            file_str = f'file_{i}'
            file_text.extend([
                ['- '],
                (f'{file_str}',
                    None,
                    None,
                    None,
                    {'type': 'url', 'url': node_url}),
                (f': {url}\n',
                    None,
                    url)
            ])
        return file_text

    def _format_image_comments(self, page_url):
        image_text = []
        for i, (index, url) in enumerate(self.comment_dict['image'], 1):
            node = self.children_appended[index]
            node_url = page_url + f'#{node["id"]}'.replace('-', '')
            if image_text == []:
                image_text.append(["Unaudited Images:\n"])
            image_str = f'image_{i}'
            image_text.extend([
                ['- '],
                (f'{image_str}',
                    None,
                    None,
                    None,
                    {'type': 'url', 'url': node_url}),
                (f': {url}\n',
                    None,
                    url)
            ])
        return image_text

    def _copy_to_destination(self):
        if 'schema' in self.destination.__dict__:
            self._database_error()
        elif '_block' in self.destination.__dict__:
            page = self.destination
            destination_children = self.destination.block.children
        else:
            page = self.destination.page
            destination_children = self.destination.children
        for child in self.children_appended:
            block = self.client.wrap_notion_block(child, page, True)
            destination_children.append(block)

    def _audit_column(self, child, i):
        col_list_children = Children(client=self.client)
        for index, kid in enumerate(child.children):
            if kid.notion_type == 'column_list':
                col_list_children.append(child.children.pop(index))
        child.children._format_for_copy()
        self.child_data['column']['children'] = child.children.notion_children
        if col_list_children:
            self.child_dict[i] = col_list_children

    def _audit_file_or_image(self, i, notion_type):
        notion_data = self.child_data[notion_type]
        if notion_data['type'] == 'file':
            notion_data['type'] = 'external'
            notion_data['external'] = {
                'url': (
                    'https://i1.wp.com/cornellsun.com/wp-content/uploads/2020/06/159'
                    '1119073-screen_shot_2020-06-02_at_10.30.13_am.png?fit=700%2C652&ssl=1'
                )
            }
            self.comment_dict[notion_type].append((i, notion_data["file"]["url"]))
            del notion_data['file']

    def _audit_pdf(self, i):
        notion_data = self.child_data['pdf']
        if notion_data['type'] == 'file':
            notion_data['type'] = 'external'
            notion_data['external'] = {
                'url': (
                    'https://reportstream.cdc.gov/assets/pdf/Report'
                    'Stream-Programmers-Guide-v2.3-updated.pdf'
                )
            }
            self.comment_dict['pdf'].append((i, notion_data["file"]["url"]))
            del notion_data['file']

    def _audit_links(self, current_index):
        notion_data = self.child_data['link_to_page']
        title, node_id = self._retrieve_link_info(notion_data)
        if title in self.link_dict:
            if self.link_dict[title] != node_id:
                notion_data[notion_data['type']]\
                    = self.link_dict[title]
        else:
            self.comment_dict['link'].append((current_index, title))

    def _audit_mentions(self, current_index):
        notion_data = self.child_data['paragraph']
        for text in notion_data['rich_text']:
            if text['type'] == 'mention' and text['mention']['type'] in ['page', 'database']:
                title, node_id = self._retrieve_link_info(text['mention'])
                if title in self.link_dict:
                    if self.link_dict[title] != node_id:
                        mention_type = text['mention']['type']
                        text['mention'][mention_type]['id']\
                            = self.link_dict[title]
                else:
                    self.comment_dict['link'].append((current_index, title))

    def _recursively_copy_children(self):
        for index, children in self.child_dict.items():
            parent_id = self.children_appended[index]['id']
            parent = self._retrieve_node(parent_id)
            parent = children.copy_to(parent, False)
            start = len(parent.children) - len(children)
            self.children_appended[index]['children'] = parent.children.block_list[start:]

    def _retrieve_node(self, node_id):
        node = self.client.get_page_or_database(node_id)
        if node is not None:
            return node
        return self.client.get_block(node_id, self.page)

    def _probe_destination_links(self):
        if '_block' in self.destination.__dict__:
            for child in self.destination.block.children:
                self._find_links(child)
        elif 'schema' in self.destination.__dict__:
            self._database_error()
        else:
            for child in self.destination.children:
                self._find_links(child)

    def _database_error(self):
        raise NotImplementedError(
            'This functionality is not yet supported for Databases'
        )

    def _find_links(self, child):
        if isinstance(child, LinkToPageBlock):
            self._store_link_info(child.notion_data)
        elif isinstance(child, ParagraphBlock):
            for text in child.notion_data['rich_text']:
                if text['type'] == 'mention' and \
                text['mention']['type'] in ['page', 'database']:  # noqa: E122
                    self._store_link_info(text['mention'])
        if child.children:
            for child in child.children:
                self._find_links(child)

    def _store_link_info(self, notion_data):
        title, link_id = self._retrieve_link_info(notion_data)
        if title != self.default_link_title and title not in self.link_dict:
            self.link_dict[title] = link_id

    def _retrieve_link_info(self, notion_data):
        node_id = notion_data[notion_data['type']] if\
            isinstance(notion_data[notion_data['type']], str) else\
            notion_data[notion_data['type']]['id']
        if "page" in notion_data['type']:
            node = self.client.get_page(node_id)
        elif "database" in notion_data['type']:
            node = self.client.get_database(node_id)
        else:
            raise NotImplementedError(f"Unknown link type: {notion_data['type']}")
        if node is None:
            msg = "Permission denied when attempting to access linked node [%s]"
            logger.warning(msg, node_id)
            return self.default_link_title, node_id
        else:
            return node.title.to_plain_text(), node_id

    def _define_page(self):
        if 'schema' in self.destination.__dict__:
            self._database_error()
        elif '_block' in self.destination.__dict__:
            self.page = self.destination
        else:
            self.page = self.destination.page
        if not self.page:
            raise NotImplementedError(
                'Page must be defined.'
            )

    def _default_info(self):
        self.comment_dict = {
            'pdf': [],
            'file': [],
            'link': [],
            'image': [],
        }
        self.link_dict = {}
        self.child_data = {}
        self.child_dict = {}
        self.notion_children = []
        self.children_appended = []
        self.child_pages_or_databases = []


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

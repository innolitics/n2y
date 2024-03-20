"""
The JinjaRenderPage plugin makes it possible to use Jinja2 templates to render
content from Notion databases into the Pandoc AST.

In addition to the raw power of Jinja2, this plugin provides a few useful Jinja
filters and context variables. One variable in particular, the FirstPassOutput
object, is used to make it possible to render content in two passes. This is
useful for rendering content that depends on other content in the same page. For
example, if one ones to generate a glossary from a centralized "Terms" database
and to only include terms which are present on the page, one can use the
FirstPassOutput filter to first generate the content of the page, and then make
a second pass to render the glossary.

Since the FirstPassOutput object requires a full render of the page, this plugin
overrides the Page class.

In addition, it also overrides the CodeBlock class.

Any code block whose caption begins with "{jinja=pandoc_format}" will be rendered
using Jinja2 into text, which in turn will be parsed by Pandoc into assuming it
follows the pandoc_format, into the AST. Thus, the jinja can be used to render
latex, html, or any other format that Pandoc supports into the AST.

Another context variable that is provided is the database variable, which is
used to access Notion databases. Any database that is @-mentioned in the caption
of the codeblock may be accessed via the database name.
"""

import functools
import re
import traceback

import jinja2
import pandoc
from pandoc.types import Code, Meta, MetaString, Pandoc, Para, Plain, Str

from n2y.blocks import FencedCodeBlock, HeadingBlock
from n2y.errors import UseNextClass
from n2y.export import database_to_yaml
from n2y.mentions import DatabaseMention
from n2y.page import Page
from n2y.rich_text import MentionRichText
from n2y.utils import available_from_list, pandoc_ast_to_markdown


def join_to(foreign_keys, table, primary_key="notion_id"):
    """
    Given a set of ids for an object, and a list of the objects these ids refer
    to, select out the objects by joining using the specified primary key
    (which defaults to 'id').
    """
    joined = []
    for foreign_key in foreign_keys:
        selected_row = None
        for row in table:
            if row[primary_key] == foreign_key:
                selected_row = row
                break
        joined.append(selected_row)
    return joined


def list_matches(string, text):
    return list(
        re.finditer(
            "(?<![a-zA-Z])" + re.escape(_canonicalize(string)) + "(?:s|es)?(?![a-zA-Z])",
            _canonicalize(text),
            re.IGNORECASE,
        )
    )


def remove_words(words, text):
    for word in words:
        first, last = word.span()
        text = text[:first] + " " * (last - first) + text[last:]
    return text


def _fuzzy_find_in(term_list, text, key="Name", by_length=True, reverse=True):
    found = []
    key_filter = lambda d: len(d[key]) if by_length else d[key]
    sorted_term_list = sorted(term_list, key=key_filter, reverse=reverse)
    if key in term_list[0]:
        for term in sorted_term_list:
            if key in term and term[key] != "":
                matches = list_matches(term[key], text)
                if matches != []:
                    found.append(term)
                    text = remove_words(matches, text)
    return found


def fuzzy_find_in(term_list, text, key="Name", by_length=True, reverse=True):
    """
    Used to search a markdown string, which may have been modified using pandoc's smart extension,
    for the value at a specified key in a dicionary for all dictionaries in a given list of them.

    see https://pandoc.org/MANUAL.html#extension-smart
    """
    found = []

    if isinstance(key, str):
        found = _fuzzy_find_in(term_list, text, key, by_length, reverse)
    elif isinstance(key, list):
        keys = key
        for key in keys:
            terms_found = fuzzy_find_in(term_list, text, key, by_length, reverse)
            found.extend(terms_found)

    return found


def _canonicalize(markdown):
    markdown = markdown.replace("\u201d", '"').replace("\u201c", '"')
    markdown = markdown.replace("\u2019", "'").replace("\u2018", "'")
    markdown = markdown.replace("\u2013", "--").replace("\u2014", "---")
    markdown = markdown.replace("\u2026", "...")
    markdown = markdown.replace("\u00a0", " ")
    return markdown


def _create_jinja_environment():
    environment = jinja2.Environment(
        cache_size=0,
        undefined=jinja2.StrictUndefined,
        extensions=["jinja2.ext.do"],
    )
    environment.globals["first_pass_output"] = FirstPassOutput()
    environment.filters["fuzzy_find_in"] = fuzzy_find_in
    environment.filters["join_to"] = join_to
    return environment


def render_from_string(source, context=None, environment=None):
    if environment is None:
        environment: jinja2.Environment = _create_jinja_environment()
    if context is None:
        context = {}
    template = environment.from_string(source)
    output = template.render(context)

    # output string usually loses trailing new line.
    if output and output[-1] != "\n":
        output += "\n"
    return output


class JinjaExceptionInfo:
    err: Exception
    obj: object
    method: str
    args: list
    kwargs: dict | None

    def __init__(self, object, err, method, args, kwargs):
        self.obj = object
        self.method = method
        self.kwargs = kwargs
        self.args = args
        self.err = err


class JinjaCacheObject(dict):
    def __init__(self, *args, block=None, **kwargs):
        if block is None:
            raise ValueError(
                f"block must be specified when instantiating {self.__class__}."
            )
        self.block = block
        super().__init__(*args, **kwargs)

    def __getitem__(self, __key):
        try:
            return super().__getitem__(__key)
        except Exception as err:
            self.cache_exception_info(err, "__getitem__", [__key])
            raise

    def cache_exception_info(self, *args, kwargs=None):
        self.block.exc_info = JinjaExceptionInfo(self, *args, kwargs)


class JinjaDatabaseItem(JinjaCacheObject): ...  # noqa: E701


class PageProperties(JinjaCacheObject): ...  # noqa: E701


class JinjaDatabaseCache(JinjaCacheObject):
    def __getitem__(self, __key):
        try:
            if isinstance(__key, str):
                return super().__getitem__(__key)
            elif isinstance(__key, int):
                return super().__getitem__(list(self)[__key])
        except Exception as err:
            self.cache_exception_info(err, "__getitem__", [__key])
            raise
        self.block.client.logger.error(
            "Jinja template database must be selected using a string or an integer"
        )
        err = KeyError(__key)
        self.cache_exception_info(err, "__getitem__", [__key])
        raise err

    def __setitem__(self, __key: str, __value: list):
        return super().__setitem__(
            __key, [JinjaDatabaseItem(item, block=self.block) for item in __value]
        )


class FirstPassOutput:
    def __init__(self, lines=None):
        self._second_pass_is_requested = False
        self._lines = lines
        self._source = None

    def __bool__(self):
        return bool(self._lines)

    def request_second_pass(self):
        self._second_pass_is_requested = True

    @property
    def is_second_pass(self):
        return self._lines is not None

    @property
    def second_pass_is_requested(self):
        return not self.is_second_pass and self._second_pass_is_requested

    @property
    def lines(self):
        self.is_second_pass or self.request_second_pass()
        return self._lines or []

    def set_lines(self, lines):
        self._lines = lines

    @property
    def source(self):
        if self._source is None or self.is_second_pass:
            self._source = "\n".join(self.lines)
        return self._source


class JinjaRenderPage(Page):
    def __init__(self, client, notion_data):
        super().__init__(client, notion_data)
        if "jinjarenderpage" not in client.plugin_data:
            client.plugin_data["jinjarenderpage"] = {}
        if self.notion_id not in client.plugin_data["jinjarenderpage"]:
            self.jinja_environment = _create_jinja_environment()
            client.plugin_data["jinjarenderpage"][self.notion_id] = {
                "environment": self.jinja_environment,
            }
        else:
            self.jinja_environment = client.plugin_data["jinjarenderpage"][
                self.notion_id
            ]["environment"]

    def to_pandoc(self, ignore_toc=False):
        ast = super().to_pandoc(ignore_toc=True)
        first_pass_output = self.jinja_environment.globals["first_pass_output"]
        if first_pass_output.second_pass_is_requested:
            first_pass_output_text = pandoc_ast_to_markdown(ast, self.client.logger)
            first_pass_output.set_lines(first_pass_output_text.splitlines(keepends=True))
            ast = super().to_pandoc(ignore_toc=True)
            jinja2.clear_caches()
        return ast if ignore_toc else self.generate_toc(ast)


class JinjaFencedCodeBlock(FencedCodeBlock):
    trigger_regex = re.compile(r"^{jinja=(.+)}")

    def __init__(self, client, notion_data, page, get_children=True):
        super().__init__(client, notion_data, page, get_children)
        result = self.caption.matches(self.trigger_regex)
        if result:
            self.pandoc_format: str = result.group(1)
        else:
            raise UseNextClass()
        self.render_count: int = 0
        self.rendered_text: str = ""
        self.error: str | None = None
        self.exc_info: JinjaExceptionInfo | None = None
        self.databases: JinjaDatabaseCache | None = None
        self.jinja_code: str = self.rich_text.to_plain_text()
        self.uses_first_pass_output: bool = "first_pass_output" in self.jinja_code
        self.page_props: PageProperties = self.page.properties_to_values(
            self.pandoc_format
        )
        self.jinja_environment: jinja2.Environment = self.client.plugin_data[
            "jinjarenderpage"
        ][self.page.notion_id]["environment"]

    def _get_database_ids_from_mentions(self):
        for rich_text in self.caption:
            is_mention = isinstance(rich_text, MentionRichText)
            if is_mention and isinstance(rich_text.mention, DatabaseMention):
                yield rich_text.mention.notion_database_id

    def _get_yaml_from_mentions(self):
        self.databases = JinjaDatabaseCache(block=self)
        export_defaults = self.client.export_defaults
        for database_id in self._get_database_ids_from_mentions():
            database = self.client.get_database(database_id)
            # TODO: Rethink about the database data is accessed from within the
            # templates; perhaps it should be something more like Django's ORM
            # where we can filter and sort the databases via the API, instead of
            # having to pull in ALL of the data first before filtering it.
            # Such an API would also alleviate the need to pass in the export
            # defaults and it could provide a mechanism to access the page
            # content from within the Jinja templates, which isn't possible
            # right now.
            if (database_name := database.title.to_plain_text()) in self.databases:
                msg = (
                    f'Duplicate database name "{database_name}"'
                    f" when rendering [{self.notion_url}]"
                )
                self.client.logger.error(msg)
                raise ValueError(msg)
            self.databases[database_name] = database_to_yaml(
                database=database,
                pandoc_format=self.pandoc_format,
                pandoc_options=[],
                id_property=export_defaults["id_property"],
                url_property=export_defaults["url_property"],
            )

    def _specify_err_msg(self, err: Exception):
        block_ref: str = f"See the Notion code block here: {self.notion_url}."
        line_num: str = traceback.format_exc().split('>", line ')[1][0]

        if self.exc_info is not None:
            if type(self.exc_info.err) is KeyError:
                if type(self.exc_info.obj) is JinjaDatabaseCache:
                    available_props: str = available_from_list(
                        list(self.exc_info.obj), "database", "databases"
                    )
                    return (
                        f' You attempted to access the "{self.exc_info.args[0]}" database'
                        f" on line {line_num} of said template, but {available_props}."
                        " Note that databases must be mentioned in the Notion code"
                        " block's caption to be available and the plugin must have"
                        " permission to read the database via the NOTION_ACCESS_TOKEN."
                        f" {block_ref}"
                    )
                elif type(self.exc_info.obj) is JinjaDatabaseItem:
                    available_props: str = available_from_list(
                        list(self.exc_info.obj), "property", "properties"
                    )
                    return (
                        f' You attempted to access the "{self.exc_info.args[0]}" property'
                        f" of a database item on line {line_num} of said template, but"
                        f" {available_props}. {block_ref}"
                    )
                elif type(self.exc_info.obj) is PageProperties:
                    available_props: str = available_from_list(
                        list(self.exc_info.obj), "property", "properties"
                    )
                    return (
                        f' You attempted to access the "{self.exc_info.args[0]}" property'
                        f" of this page on line {line_num} of said template, but"
                        f" {available_props}. {block_ref}"
                    )
            elif self.exc_info.obj in ["test", "filter"]:
                return (
                    f' Recieved the message "{str(err)}" when evaluating line {line_num}.'
                    f' The Jinja {self.exc_info.obj} "{self.exc_info.method}" raised'
                    " this error when called with the following argument(s):"
                    f' {{\n\t"args": {self.exc_info.args},\n\t"kwargs":'
                    f" {self.exc_info.kwargs}\n}}\n{block_ref}"
                )
        elif type(err) is jinja2.exceptions.TemplateSyntaxError:
            return (
                f" There is a syntax error in the Jinja template on line {line_num}."
                f" Recieved the message {str(err)}. {block_ref}"
            )

        return (
            f' Received the message "{str(err)}" when evaluating line {line_num}.'
            f" {block_ref}"
        )

    def _log_jinja_error(self, err: Exception):
        self.error = (
            f"Error rendering a Jinja template on {self.page.title.to_plain_text()}."
            if self.page
            else "Unknown Page."
        )
        self.error += self._specify_err_msg(err)
        self.client.logger.error(self.error)

    def _render_error(self, err, during_render=True):
        if self.render_count == 1 or during_render and self.render_count == 0:
            self._log_jinja_error(err)

    def _error_ast(self):
        return [Para([Code(("", ["markdown"], []), self.error)])]

    def _render_text(self):
        self.jinja_environment.filters = {
            k: self._debug_assist(v, "filter", k)
            for k, v in self.jinja_environment.filters.items()
        }
        self.jinja_environment.tests = {
            k: self._debug_assist(v, "test", k)
            for k, v in self.jinja_environment.tests.items()
        }
        if not getattr(self, "context", None):
            self.context = {
                "databases": self.databases,
                "page": PageProperties(self.page_props, block=self),
            }
        if "render_content" in self.jinja_code:

            def render_content(notion_id, level_adjustment=0):
                page = self.client.get_page(notion_id)
                for child in page.block.children:
                    if isinstance(child, HeadingBlock):
                        child.level = max(1, child.level + level_adjustment)
                ast = (
                    page.to_pandoc()
                    if page.to_pandoc()
                    else Pandoc(Meta({"title": MetaString(page.block.title)}), [])
                )
                content = pandoc.write(
                    ast,
                    format=self.pandoc_format,
                    options=[],
                )
                return content

            self.jinja_environment.filters["render_content"] = self._debug_assist(
                render_content, "filter", "render_content"
            )
        try:
            self.rendered_text = render_from_string(
                self.jinja_code, self.context, self.jinja_environment
            )
        except Exception as err:
            self._render_error(err)
        self.render_count += 1

    def to_pandoc(self):
        if self.databases is None:
            self._get_yaml_from_mentions()
        if self.render_count < 1 or self.render_count < 2 and self.uses_first_pass_output:
            self._render_text()
        if self.error:
            children_ast = self._error_ast()
        else:
            if self.pandoc_format != "plain":
                # pandoc.read includes Meta data, which isn't relevant here; we just
                # want the AST for the content
                try:
                    document_ast = pandoc.read(
                        self.rendered_text, format=self.pandoc_format
                    )
                    children_ast = document_ast[1]
                except Exception as err:
                    self._render_error(err, during_render=False)
                    children_ast = self._error_ast()
            else:
                # Pandoc doesn't support reading "plain" text into it's AST (since
                # if it was just plain text, why would you need pandoc to parse it!)
                # That said, sometimes it is useful to create plain text from the
                # jinja rendering (e.g., when producing a site map or something
                # similar from Notion databases).
                children_ast = Plain([Str(self.rendered_text)])
        return children_ast

    def _debug_assist(self, func, jinja_type, jinja_ref):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as err:
                if self.exc_info is None:
                    if type(args[0]) is jinja2.Environment:
                        args = list(args[1:])
                    self.exc_info = JinjaExceptionInfo(
                        jinja_type, err, jinja_ref, args, kwargs
                    )
                raise

        return wrapper


notion_classes = {
    "page": JinjaRenderPage,
    "blocks": {
        "code": JinjaFencedCodeBlock,
    },
}

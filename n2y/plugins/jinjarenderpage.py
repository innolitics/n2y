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
import re
import traceback

import pandoc
import jinja2
from pandoc.types import Plain, Str, Code, Pandoc, Meta, MetaString, Para

from n2y.page import Page
from n2y.logger import logger
from n2y.errors import UseNextClass
from n2y.export import database_to_yaml
from n2y.mentions import DatabaseMention
from n2y.rich_text import MentionRichText
from n2y.blocks import FencedCodeBlock, HeadingBlock
from n2y.utils import pandoc_ast_to_markdown, available_from_list


def join_to(foreign_keys, table, primary_key='notion_id'):
    '''
    Given a set of ids for an object, and a list of the objects these ids refer
    to, select out the objects by joining using the specified primary key
    (which defaults to 'id').
    '''
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
    return list(re.finditer(
        '(?<![a-zA-Z])' + re.escape(_canonicalize(string)) + '(?:s|es)?(?![a-zA-Z])',
        _canonicalize(text), re.IGNORECASE)
    )


def remove_words(words, text):
    for word in words:
        span = word.span()
        text = text[:span[0]] + ' ' * (span[1] - span[0]) + text[span[1]:]
    return text


def _fuzzy_find_in(term_list, text, key='Name', by_length=True, reverse=True):
    found = []
    key_filter = lambda d: len(d[key]) if by_length else d[key]
    sorted_term_list = sorted(term_list, key=key_filter, reverse=reverse)
    if key in term_list[0]:
        for term in sorted_term_list:
            if key in term and term[key] != '':
                matches = list_matches(term[key], text)
                if matches != []:
                    found.append(term)
                    text = remove_words(matches, text)
    return found


def fuzzy_find_in(term_list, text, key='Name', by_length=True, reverse=True):
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
    markdown = markdown.replace('\u201D', '"').replace('\u201C', '"')
    markdown = markdown.replace('\u2019', "'").replace('\u2018', "'")
    markdown = markdown.replace('\u2013', '--').replace('\u2014', '---')
    markdown = markdown.replace('\u2026', '...')
    markdown = markdown.replace('\u00A0', ' ')
    return markdown


def _create_jinja_environment():
    environment = jinja2.Environment(
        cache_size=0,
        undefined=jinja2.StrictUndefined,
        extensions=["jinja2.ext.do"],
    )
    environment.globals['first_pass_output'] = FirstPassOutput()
    environment.filters['fuzzy_find_in'] = fuzzy_find_in
    environment.filters['join_to'] = join_to
    return environment


def render_from_string(source, context=None, environment=None):
    if environment is None:
        environment: jinja2.Environment = _create_jinja_environment()
    if context is None:
        context = {}
    template = environment.from_string(source)
    template.root_render_func
    output = template.render(context)

    # output string usually loses trailing new line.
    if output and output[-1] != '\n':
        output += '\n'
    return output


class JinjaExceptionInfo:
    err: Exception
    object: object
    method: str
    args: list
    kwargs: dict | None

    def __init__(self, object, err, method, args, kwargs):
        self.object = object
        self.method = method
        self.kwargs = kwargs
        self.args = args
        self.err = err


class JinjaCacheObject(dict):
    def __init__(self, *args, block=None, **kwargs):
        if block is None:
            raise ValueError(f'block must be specified when instantiating {self.__class__}.')
        self.block = block
        super().__init__(*args, **kwargs)

    def __getitem__(self, __key):
        try:
            return super().__getitem__(__key)
        except Exception as err:
            self.cache_exception_info(err, '__getitem__', [__key])
            raise

    def cache_exception_info(self, *args, kwargs=None):
        self.block.exc_info = JinjaExceptionInfo(self, *args, kwargs)


class JinjaDatabaseItem(JinjaCacheObject):
    ...

class PageProperties(JinjaCacheObject):
    ...

class JinjaDatabaseCache(JinjaCacheObject):
    def __getitem__(self, __key):
        try:
            if isinstance(__key, str):
                return super().__getitem__(__key)
            elif isinstance(__key, int):
                return super().__getitem__(list(self)[__key])
        except Exception as err:
            self.cache_exception_info(err, '__getitem__', [__key])
            raise
        logger.error((
            'Jinja template database must be '
            'selected using a string or an integer'
        ))
        err = KeyError(__key)
        self.cache_exception_info(err, '__getitem__', [__key])
        raise err

    def __setitem__(self, __key: str, __value: list):
        return super().__setitem__(__key, [JinjaDatabaseItem(item, block=self.block) for item in __value])



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
            self._source = '\n'.join(self.lines)
        return self._source


class JinjaRenderPage(Page):
    def __init__(self, client, notion_data):
        super().__init__(client, notion_data)
        if 'jinjarenderpage' not in client.plugin_data:
            client.plugin_data['jinjarenderpage'] = {}
        if self.notion_id not in client.plugin_data['jinjarenderpage']:
            self.jinja_environment = _create_jinja_environment()
            client.plugin_data['jinjarenderpage'][self.notion_id] = {
                'environment': self.jinja_environment,
            }
        else:
            self.jinja_environment = client.plugin_data['jinjarenderpage']\
                [self.notion_id]['environment']

    def to_pandoc(self, ignore_toc=False):
        ast = super().to_pandoc(ignore_toc=True)
        first_pass_output = self.jinja_environment.globals["first_pass_output"]
        if first_pass_output.second_pass_is_requested:
            first_pass_output_text = pandoc_ast_to_markdown(ast)
            first_pass_output.set_lines(first_pass_output_text.splitlines(keepends=True))
            ast = super().to_pandoc(ignore_toc=True)
            jinja2.clear_caches()
        return ast if ignore_toc else self.generate_toc(ast)


class JinjaFencedCodeBlock(FencedCodeBlock):
    trigger_regex = re.compile(r'^{jinja=(.+)}')

    def __init__(self, client, notion_data, page, get_children=True):
        super().__init__(client, notion_data, page, get_children)
        result = self.caption.matches(self.trigger_regex)
        if result:
            self.pandoc_format: str = result.group(1)
        else:
            raise UseNextClass()
        self.render_count: int = 0
        self.rendered_text: str = ''
        self.error: str | None = None
        self.exc_info: JinjaExceptionInfo | None = None
        self.databases: JinjaDatabaseCache | None = None
        self.page_props: PageProperties = self.page.properties_to_values(self.pandoc_format)
        self.jinja_environment: jinja2.Environment = self.client.plugin_data[
            'jinjarenderpage'][self.page.notion_id]['environment']

    def _get_database_ids_from_mentions(self):
        for rich_text in self.caption:
            is_mention = isinstance(rich_text, MentionRichText)
            if is_mention and isinstance(rich_text.mention, DatabaseMention):
                yield rich_text.mention.notion_database_id

    def _get_yaml_from_mentions(self):
        self.databases = JinjaDatabaseCache(block=self)
        export_defaults = self.client.export_defaults
        for i, database_id in enumerate(self._get_database_ids_from_mentions()):
            notion_database = self.client.get_database(database_id)
            # TODO: Rethink about the database data is accessed from within the
            # templates; perhaps it should be something more like Django's ORM
            # where we can filter and sort the databases via the API, instead of
            # having to pull in ALL of the data first before filtering it.
            # Such an API would also alleviate the need to pass in the export
            # defaults and it could provide a mechanism to access the page
            # content from within the Jinja templates, which isn't possible
            # right now.
            if (database_name := notion_database.title.to_plain_text()) in self.databases:
                msg = (
                    f'Duplicate database name "{database_name}"'
                    f' when rendering [{self.notion_url}]'
                )
                logger.error(msg)
                raise ValueError(msg)
            database = database_to_yaml(
                database=notion_database,
                pandoc_format=self.pandoc_format,
                pandoc_options=[],
                id_property=export_defaults["id_property"],
                url_property=export_defaults["url_property"],
            )
            if database is None:
                ordinal = lambda x: [
                    "first",
                    "second",
                    "third",
                    "fourth",
                    "fifth",
                    "sixth",
                    "seventh",
                    "eighth",
                    "ninth",
                    "tenth",
                    "eleventh",
                    "twelfth"
                ][x]
                logger.error(
                    ' Error retrieving databases for a Jinja template on ' + \
                    self.page.title.to_plain_text() + '.' + f'The {ordinal(i)}' + \
                    ' database attemted to access was not found. See the Notion' + \
                    f' code block here: {self.notion_url}.'
                )
            self.databases[database_name] = database

    def _specify_err_msg(self, msg):
        block_ref:str = f' See the Notion code block here: {self.notion_url}.'
        line_num: str = traceback.format_exc().split('\n  File "<template>", line ')[1][0]
        message: str = msg
        if self.exc_info is not None:
            if type(self.exc_info.object) is JinjaDatabaseCache:
                if type(self.exc_info.err) is KeyError:
                    available_props = available_from_list(
                        list(self.exc_info.object),
                        'database', 'databases'
                    )
                    return f' You attempted to access the "{self.exc_info.args[0]}" database on ' + \
                        f'line {line_num} of said template, but ' + available_props + '. Note ' + \
                        "that databases must be mentioned in the Notion code block's caption to" + \
                        ' be available and the plugin must have permission to read the database' + \
                        ' via the NOTION_ACCESS_TOKEN.' + block_ref
            elif type(self.exc_info.object) is JinjaDatabaseItem:
                if type(self.exc_info.err) is KeyError:
                    available_props = available_from_list(
                        list(self.exc_info.object),
                        'property', 'properties'
                    )
                    return f' You attempted to access the "{self.exc_info.args[0]}" property ' + \
                        f'of a database item on line {line_num} of said template, but ' + \
                        available_props + '.' + block_ref
            elif type(self.exc_info.object) is PageProperties:
                if type(self.exc_info.err) is KeyError:
                    available_props = available_from_list(
                        list(self.exc_info.object),
                        'property', 'properties'
                    )
                    return f' You attempted to access the "{self.exc_info.args[0]}" property' + \
                        f' of this page on line {line_num} of said template, but ' + \
                        available_props + '.' + block_ref
        if (db_err := "JinjaDatabaseCache object' has no attribute '") in message:
            split_msg = msg.split(db_err)
            available_props = available_from_list(
                list(self.databases.keys()),
                "database", "databases"
            )
            return f' You attempted to access the "{split_msg[1][:-1]}" database. ' + \
                available_props + '.  Note that databases must be mentioned in the' + \
                " Notion code block's caption to be available. Also, note that the" + \
                ' plugin must have permission to read the database via the' + \
                ' NOTION_ACCESS_TOKEN.' + block_ref
        elif (pg_err := "PageProperties object' has no attribute '") in msg:
            split_msg = msg.split(pg_err)
            available_props = available_from_list(
                list(self.page_props.keys()),
                "property", "properties"
            )
            return f' You attempted to access the "{split_msg[1][:-1]}" page property. ' + \
                available_props + '.' + block_ref

        traceback_msg = traceback.format_exc()
        # if (dict_err := "dict object' has no attribute '") in msg:
        #     split_msg = msg.split(dict_err)
        #     target_attr = split_msg[1][:-1]
        #     line_index = int(traceback_msg.split('\n  File "<template>", line ')[1][0]) - 1
        #     line = self.jinja_code.splitlines()[line_index]
        #     available_props = available_from_list(
        #         list(self.context.keys()),
        #         "variable", "variables"
        #     )
        #     return f' You attempted to access the "{split_msg[1][:-1]}" variable. ' + \
        #         available_props + '.' + block_ref
        return ' ' + msg + block_ref + '\n' + traceback_msg

    def _log_jinja_error(self, err):
        message = str(err)
        self.error = (
            'Error rendering a Jinja template on '
            f'{self.page.title.to_plain_text()}.' if self.page else 'Unknown Page'
        )
        self.error += self._specify_err_msg(message)
        logger.error(self.error)

    def _render_error(self, err, during_render=True):
        first_pass_output = self.jinja_environment.globals["first_pass_output"]
        if self.render_count == 1 or during_render and self.render_count == 0 and \
                not first_pass_output.second_pass_is_requested:
            self._log_jinja_error(err)

    def _error_ast(self):
        return [Para([Code(('', ['markdown'], []), self.error)])]

    def _render_text(self):
        if not getattr(self, 'jinja_code', None):
            self.jinja_code = self.rich_text.to_plain_text()
        if not getattr(self, 'context', None):
            self.context = {
                "databases": self.databases,
                "page": PageProperties(self.page_props, block=self),
            }
        if 'render_content' in self.jinja_code:
            def render_content(notion_id, level_adjustment=0):
                page = self.client.get_page(notion_id)
                for child in page.block.children:
                    if isinstance(child, HeadingBlock):
                        child.level = max(1, child.level + level_adjustment)
                ast = page.to_pandoc() if page.to_pandoc() else \
                    Pandoc(Meta({'title': MetaString(page.block.title)}), [])
                content = pandoc.write(
                    ast,
                    format=self.pandoc_format,
                    options=[],
                )
                return content
            self.jinja_environment.filters['render_content'] = render_content
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
        if self.render_count < 2:
            self._render_text()
        if self.error:
            children_ast = self._error_ast()
        else:
            if self.pandoc_format != "plain":
                # pandoc.read includes Meta data, which isn't relevant here; we just
                # want the AST for the content
                try:
                    document_ast = pandoc.read(self.rendered_text, format=self.pandoc_format)
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

    def _print_context_debug(self, context):
        logger.info("Databases")
        for database_name, database in context["databases"].items():
            logger.info("  %s [%d]", database_name, len(database))
            if len(database) > 0:
                for key in database[0]:
                    logger.info("    %s", key)
        logger.info("page")
        for key, value in context["page"].items():
            logger.info("  %s: %r", key, value)


notion_classes = {
    "page": JinjaRenderPage,
    "blocks": {
        "code": JinjaFencedCodeBlock,
    }
}

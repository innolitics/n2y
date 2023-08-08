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
from jinja2.exceptions import TemplateSyntaxError, UndefinedError
from pandoc.types import Plain, Str, Code, Pandoc, Meta, MetaString, Para

from n2y.page import Page
from n2y.logger import logger
from n2y.errors import UseNextClass
from n2y.export import database_to_yaml
from n2y.mentions import DatabaseMention
from n2y.rich_text import MentionRichText
from n2y.blocks import FencedCodeBlock, HeadingBlock
from n2y.utils import pandoc_ast_to_markdown, available_from_list


class JinjaDatabaseCache(dict):
    def __getitem__(self, key):
        if isinstance(key, str):
            return super().__getitem__(key)
        elif isinstance(key, int):
            return super().__getitem__(list(self)[key])
        logger.error((
            'Jinja template database must be '
            'selected using a string or an integer'
        ))
        raise KeyError(key)


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
        environment = _create_jinja_environment()
    if context is None:
        context = {}
    template = environment.from_string(source)
    output = template.render(context)

    # output string usually loses trailing new line.
    if output and output[-1] != '\n':
        output += '\n'
    return output


class JinjaRenderPage(Page):
    def __init__(self, client, notion_data):
        super().__init__(client, notion_data)
        if 'jinjarenderpage' not in client.plugin_data:
            client.plugin_data['jinjarenderpage'] = {}
        if self.notion_id not in client.plugin_data:
            client.plugin_data['jinjarenderpage'][self.notion_id] = {
                'environment': _create_jinja_environment(),
            }

    def to_pandoc(self):
        first_pass_ast = super().to_pandoc()
        jinja_environment = self.client.plugin_data[
            'jinjarenderpage'][self.notion_id]['environment']
        first_pass_output = jinja_environment.globals["first_pass_output"]
        if first_pass_output.second_pass_is_requested:
            first_pass_output_text = pandoc_ast_to_markdown(first_pass_ast)
            first_pass_output.set_lines(first_pass_output_text.splitlines(keepends=True))
            second_pass_ast = super().to_pandoc()
            jinja2.clear_caches()
            return second_pass_ast
        else:
            return first_pass_ast


class JinjaFencedCodeBlock(FencedCodeBlock):
    trigger_regex = re.compile(r'^{jinja=(.+)}')

    def __init__(self, client, notion_data, page, get_children=True):
        super().__init__(client, notion_data, page, get_children)
        result = self.caption.matches(self.trigger_regex)
        if result:
            self.pandoc_format = result.group(1)
        else:
            raise UseNextClass()
        self.error = None
        self.render_count = 0
        self.rendered_text = ''
        self.mentions_processed = False
        self.databases = JinjaDatabaseCache()

    def _get_database_ids_from_mentions(self):
        for rich_text in self.caption:
            is_mention = isinstance(rich_text, MentionRichText)
            if is_mention and isinstance(rich_text.mention, DatabaseMention):
                yield rich_text.mention.notion_database_id

    def _get_yaml_from_mentions(self):
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
            database_name = database.title.to_plain_text()
            if database_name in self.databases:
                msg = (
                    f'Duplicate database name "{database_name}"'
                    f' when rendering [{self.notion_url}]'
                )
                logger.error(msg)
                raise ValueError(msg)
            self.databases[database_name] = database_to_yaml(
                database=database,
                pandoc_format=self.pandoc_format,
                pandoc_options=[],
                id_property=export_defaults["id_property"],
                url_property=export_defaults["url_property"],
            )
        self.mentions_processed = True

    def _log_jinja_error(self, err):
        message = str(err)
        block_ref = f'\nSee the Notion code block here: {self.notion_url}.'
        self.error = (
            'Error rendering Jinja template on page: ' +
            f'{self.page.title.to_plain_text()}.' if self.page else 'Unknown'
        )

        if (db_err := "JinjaDatabaseCache object' has no attribute '") in message:
            split_msg = message.split(db_err)
            specific_msg = (
                f' You attempted to access the "{split_msg[1][:-1]}" database. '
                f'{available_from_list(list(self.databases.keys()), "database", "databases")}.'
                " Note that databases must be mentioned in the Notion code block's caption to "
                'be available. Also, note that the plugin must have permission to read the '
                'database via the NOTION_ACCESS_TOKEN'
            )
        elif (pg_err := "PageProperties object' has no attribute '") in message:
            split_msg = message.split(pg_err)
            specific_msg = (
                f' You attempted to access the "{split_msg[1][:-1]}" page property. '
                f'{available_from_list(list(self.page_props.keys()), "property", "properties")}.'
            )
        else:
            specific_msg = None

        if specific_msg:
            self.error += specific_msg + block_ref
        else:
            self.error += f' {message}' + block_ref + f'\n{traceback.format_exc()}'
        logger.error(self.error)

    def _render_error(self, err, during_render=True):
        jinja_environment = self.client.plugin_data[
            'jinjarenderpage'][self.page.notion_id]['environment']
        first_pass_output = jinja_environment.globals["first_pass_output"]
        only_one_pass = self.render_count == 0 and not first_pass_output.second_pass_is_requested
        if during_render and only_one_pass or self.render_count == 1:
            self._log_jinja_error(err)

    def _error_ast(self):
        return [Para([Code(('', ['markdown'], []), self.error)])]

    def _render_text(self):
        self.page_props = self.page.properties_to_values(self.pandoc_format)
        jinja_environment = self.client.plugin_data[
            'jinjarenderpage'][self.page.notion_id]['environment']
        jinja_code = self.rich_text.to_plain_text()
        context = {
            "databases": self.databases,
            "page": self.page_props,
        }
        if 'render_content' in jinja_code:
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
            self.client.plugin_data['jinjarenderpage'][self.page.notion_id][
                'environment'].filters['render_content'] = render_content
        try:
            self.rendered_text = render_from_string(jinja_code, context, jinja_environment)
        except (UndefinedError, TemplateSyntaxError) as err:
            self._render_error(err)
        self.render_count += 1

    def to_pandoc(self):
        if not self.mentions_processed:
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

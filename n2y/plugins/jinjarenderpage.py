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
import logging

import pandoc
import jinja2
from jinja2.exceptions import TemplateSyntaxError, UndefinedError
from n2y.blocks import FencedCodeBlock
from n2y.errors import UseNextClass
from n2y.mentions import DatabaseMention

from n2y.page import Page
from n2y.rich_text import MentionRichText
from n2y.utils import pandoc_ast_to_markdown
from n2y.export import database_to_yaml


logger = logging.getLogger(__name__)


class FirstPassOutput:
    def __init__(self, lines=None):
        self._second_pass_is_requested = False
        if lines is None:
            lines = []
        self._lines = lines
        self._source = None

    def __bool__(self):
        return bool(self._lines)

    def request_second_pass(self):
        self._second_pass_is_requested = True

    @property
    def is_second_pass(self):
        return self._lines != []

    @property
    def second_pass_is_requested(self):
        return not self.is_second_pass and self._second_pass_is_requested

    @property
    def lines(self):
        self.is_second_pass or self.request_second_pass()
        return self._lines

    def set_lines(self, lines):
        self._lines = lines

    @property
    def source(self):
        if self._source is None or self.is_second_pass and self._source == '':
            self._source = '\n'.join(self.lines)
        return self._source


def join_to(foreign_keys, table, primary_key='id'):
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


def fuzzy_in(left, right):
    """
    Used to compare markdown strings which may have been modified using pandoc's smart extension.

    See https://pandoc.org/MANUAL.html#extension-smart
    """
    return _canonicalize(left) in _canonicalize(right)


def fuzzy_search(string, pattern):
    """
    Used to find a pattern in a markdown string which may have been modified using pandoc's smart extension.

    see https://pandoc.org/MANUAL.html#extension-smart
    """
    return re.findall(_canonicalize(pattern), _canonicalize(string))


def fuzzy_find_in(dict_list, string, key='Name', by_length=True, reverse=True):
    """
    Used to search a markdown string, which may have been modified using pandoc's smart extension,
    for the value at a specified key in a dicionary for all dictionaries in a given list of them.

    see https://pandoc.org/MANUAL.html#extension-smart
    """
    found = []
    key_filter = lambda d: len(d[key]) if by_length else d[key]
    sorted_dict_list = sorted(dict_list, key=key_filter, reverse=reverse)
    for term in sorted_dict_list:
        matches = list(re.finditer(
            '(?<![a-zA-Z])' + _canonicalize(term[key]) + '(?![a-zA-Z])',
            _canonicalize(string))
        )
        if matches != []:
            found.append(term)
            for match in matches:
                span = match.span()
                string = string[:span[0]] + ' ' * (span[1] - span[0]) + string[span[1]:]
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
    environment.filters['fuzzy_search'] = fuzzy_search
    environment.filters['fuzzy_in'] = fuzzy_in
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
                'database_cache': {},
            }

    def to_pandoc(self):
        first_pass_ast = super().to_pandoc()
        jinja_environment = self.client.plugin_data['jinjarenderpage']\
            [self.notion_id]['environment']
        first_pass_output = jinja_environment.globals["first_pass_output"]
        if first_pass_output.second_pass_is_requested:
            first_pass_output_text = pandoc_ast_to_markdown(first_pass_ast)
            first_pass_output.set_lines(first_pass_output_text.splitlines(keepends=True))
            super().__init__(self.client, self.notion_data)
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
        self.rendered_text = ''
        self.databases = {}

    def _get_database_ids_from_mentions(self):
        for rich_text in self.caption:
            is_mention = isinstance(rich_text, MentionRichText)
            if is_mention and isinstance(rich_text.mention, DatabaseMention):
                yield rich_text.mention.notion_database_id

    def _get_yaml_from_mentions(self):
        if self.notion_id in self.client.plugin_data['jinjarenderpage']\
            [self.page.notion_id]['database_cache']:
            self.databases = self.client.plugin_data['jinjarenderpage']\
                [self.page.notion_id]['database_cache'][self.notion_id]
        else:
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
                self.databases[database.title.to_plain_text()] = database_to_yaml(
                    database=database,
                    pandoc_format=self.pandoc_format,
                    pandoc_options=export_defaults["pandoc_options"],  # maybe shouldn't use this
                    id_property=export_defaults["id_property"],
                    url_property=export_defaults["url_property"],
                )
                self.client.plugin_data['jinjarenderpage'][self.page.notion_id]\
                    ['database_cache'][self.notion_id] = {**self.databases}

    def _render_text(self):
        jinja_environment = self.client.plugin_data['jinjarenderpage']\
            [self.page.notion_id]['environment']
        jinja_code = self.rich_text.to_plain_text()
        context = {
            "databases": self.databases,
            "page": self.page.properties_to_values(self.pandoc_format),
        }
        try:
            self.rendered_text = render_from_string(jinja_code, context, jinja_environment)
        except (UndefinedError, TemplateSyntaxError):
            logger.error(
                "Error rendering Jinja template on %s [%s]",
                self.page.title.to_plain_text() if self.page else "unknown",
                self.notion_url,
                exc_info=True,
            )
            raise

    def to_pandoc(self):
        self._get_yaml_from_mentions()
        self._render_text()
        # pandoc.read includes Meta data, which isn't relevant here; we just
        # want the AST for the content
        document_ast = pandoc.read(
            self.rendered_text,
            format=self.pandoc_format,
            options=self.client.export_defaults["pandoc_options"],
        )
        children_ast = document_ast[1]
        return children_ast


notion_classes = {
    "page": JinjaRenderPage,
    "blocks": {
        "code": JinjaFencedCodeBlock,
    }
}

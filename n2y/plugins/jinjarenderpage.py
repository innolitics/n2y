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
from n2y.blocks import FencedCodeBlock
from n2y.errors import UseNextClass

from n2y.page import Page
from n2y.utils import pandoc_ast_to_markdown


logger = logging.getLogger(__name__)


class FirstPassOutput:
    def __init__(self, lines=None):
        self._second_pass_is_requested = False
        self.is_second_pass = lines is not None
        if lines is None:
            lines = []
        self._lines = lines
        self._source = None

    def __bool__(self):
        return False

    def request_second_pass(self):
        self._second_pass_is_requested = True

    @property
    def second_pass_is_requested(self):
        return not self.is_second_pass and self._second_pass_is_requested

    @property
    def lines(self):
        self.request_second_pass()
        return self._lines

    def set_lines(self, lines):
        self._lines = lines

    @property
    def source(self):
        if self._source is None:
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
    return _canonicalize_markdown(left) in _canonicalize_markdown(right)


def _canonicalize_markdown(markdown):
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
    )
    environment.globals['first_pass_output'] = FirstPassOutput()
    environment.filters['join_to'] = join_to
    environment.filters['fuzzy_in'] = fuzzy_in
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
        self.client.plugin_data['jinjarenderpage'] = {
            'environment': _create_jinja_environment(),
        }

    def to_pandoc(self):
        first_pass_output_text = pandoc_ast_to_markdown(super().to_pandoc())
        jinja_environment = self.client.plugin_data['jinjarenderpage']['environment']
        first_pass_output = jinja_environment.globals["first_pass_output"]
        first_pass_output.set_lines(first_pass_output_text.splitlines(keepends=True))
        jinja2.clear_caches()
        return super().to_pandoc()


class JinjaFencedCodeBlock(FencedCodeBlock):
    trigger_regex = re.compile(r'^{jinja=(.+)}')

    def __init__(self, client, notion_data, page, get_children=True):
        super().__init__(client, notion_data, page, get_children)
        result = self.caption.matches(self.trigger_regex)
        if result:
            self.pandoc_format = result.group(1)
        else:
            raise UseNextClass()
        # TODO: loop through mentions and find database IDs
        # TODO: load the databases using the notion client

    def to_pandoc(self):
        jinja_environment = self.client.plugin_data['jinjarenderpage']['environment']
        jinja_code = self.rich_text.to_plain_text()
        # TODO: get databases and add to context
        context = {}
        rendered_text = render_from_string(jinja_code, context, jinja_environment)

        # pandoc.read includes Meta data, which isn't relevant here; we just
        # want the AST for the content
        document_ast = pandoc.read(rendered_text, format=self.pandoc_format)
        children_ast = document_ast[1]
        return children_ast

# TODO: remove data files from the n2y yaml file
# TODO: make the n2y config file produce docx files directly


notion_classes = {
    "page": JinjaRenderPage,
    "blocks": {
        "code": JinjaFencedCodeBlock,
    }
}

import os
import uuid
import logging

import pandoc
import jinja2
from pandoc.types import Pandoc, Meta, MetaString

from n2y.page import Page
from n2y.utils import load_yaml, strip_hyphens


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


def generate_template_output(template_filename, context):
    environment = _create_jinja_environment()
    first_pass_output = FirstPassOutput()
    environment.globals['first_pass_output'] = first_pass_output
    output_string = generate_template_output_string(environment, template_filename, context)
    if first_pass_output.second_pass_is_requested:
        jinja2.clear_caches()
        first_pass_output_filled = FirstPassOutput(output_string.splitlines(keepends=True))
        second_pass_environment = _create_jinja_environment()
        second_pass_environment.globals['first_pass_output'] = first_pass_output_filled
        output_string = generate_template_output_string(
            second_pass_environment,
            template_filename,
            context
        )
    return output_string


def generate_template_output_string(environment, template_filename, context):
    template = environment.get_template(template_filename)
    return _generate_source_string(template, context)


def _create_jinja_environment():
    environment = jinja2.Environment(
        cache_size=0,
        undefined=jinja2.StrictUndefined,
    )
    environment.filters['join_to'] = join_to
    environment.filters['fuzzy_in'] = fuzzy_in
    return environment


def _generate_source_string(template, context):
    source = template.render(**context)
    # template output_string usually loses trailing new line.
    if source and source[-1] != '\n':
        source += '\n'
    return source


class JinjaRenderPage(Page):
    """
    Renders jinja inside code blocks in page to git flavored markdown.

    Any code block populated by jinja will be rendered into git flavored
    markdown.
    """

    def __init__(self, client, notion_data):
        super().__init__(client, notion_data)
        if 'render_context' not in client.plugin_data:
            self._store_data(client.exports)

    def to_pandoc(self):
        children = self.block.children_to_pandoc()
        return self._render(Pandoc(Meta({'title': MetaString(self.block.title)}), children))

    def _render(self, ast):
        context = self.client.plugin_data['render_context']
        parent_id = strip_hyphens(self.notion_parent['database_id'])
        pandoc_format = 'gfm'
        pandoc_options = []
        for export in self.client.exports:
            if export['id'] == parent_id:
                pandoc_format = export['pandoc_format']
                pandoc_options = export['pandoc_options']
        try:
            file_id = str(uuid.uuid4())
            template_name = f'{file_id}-template.md'
            with open(template_name, 'w') as file:
                markdown = pandoc.write(
                    ast,
                    format=pandoc_format,
                    options=pandoc_options
                )
                file.write(markdown)
            output_string = generate_template_output(template_name, context)
            rendered_ast = pandoc.read(
                output_string,
                format=pandoc_format,
                options=pandoc_options
            )
            return rendered_ast
        except Exception as err:
            parent_id = self.notion_parent['database_id']
            parent = self.client.get_database(parent_id)
            parent_title = parent.title.to_plain_text()
            title = self.title.to_plain_text()
            logger.error(
                f'Error on page titled {title} in the {parent_title} database'
            )
            raise err
        finally:
            os.remove(template_name)

    def _store_data(self, exports):
        self.client.plugin_data['render_context'] = {}
        render_context = self.client.plugin_data['render_context']
        default_data = ['Glossary', 'Documents', 'References']
        for export in exports:
            data_filename = export['output']
            if export['node_type'] == 'database_as_yaml':
                data_name, _ = os.path.splitext(os.path.basename(data_filename))
                if data_name in default_data:
                    default_data.remove(data_name)
                with open(data_filename, "r") as f:
                    data_string = f.read()
                if data_name in render_context:
                    raise ValueError(
                        'There is already data attached to the key "{}"'.format(data_name)
                    )
                yaml_data = load_yaml(data_string)
                render_context[data_name] = yaml_data
        for name in default_data:
            render_context[name] = {}


notion_classes = {
    "page": JinjaRenderPage
}

import os
import uuid
import logging
from importlib import import_module

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


def extract_module_and_class(descriptor):
    parts = descriptor.split('.')
    module_name = '.'.join(parts[:-1])
    class_name = parts[-1]
    return module_name, class_name


def post_processing_filter_list(environment):
    return getattr(environment, 'rdm_post_process_filters', [])


def load_class(class_descriptor):
    module_name, class_name = extract_module_and_class(class_descriptor)
    module = import_module(module_name)
    return getattr(module, class_name)


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


def render_template_to_file(config, template_filename, context, loaders=None):
    output_string = generate_template_output(config, template_filename, context, loaders=loaders)
    return output_string


def generate_template_output(config, template_filename, context, loaders=None):
    environment = _create_jinja_environment(config, loaders)
    first_pass_output = FirstPassOutput()
    environment.globals['first_pass_output'] = first_pass_output
    output_string = generate_template_output_string(environment, template_filename, context)
    if first_pass_output.second_pass_is_requested:
        jinja2.clear_caches()
        first_pass_output_filled = FirstPassOutput(output_string.splitlines(keepends=True))
        second_pass_environment = _create_jinja_environment(config, loaders)
        second_pass_environment.globals['first_pass_output'] = first_pass_output_filled
        output_string = generate_template_output_string(
            second_pass_environment,
            template_filename,
            context
        )
    return output_string


def generate_template_output_string(environment, template_filename, context):
    template = environment.get_template(template_filename)
    source_string = _generate_source_string(template, context)
    return source_string


def _create_jinja_environment(config, loaders=None):
    extensions = [load_class(ed) for ed in config.get('md_extensions', [])]
    loader = _create_loader(loaders)
    environment = jinja2.Environment(
        cache_size=0,
        undefined=jinja2.StrictUndefined,
        loader=loader,
        extensions=extensions,
    )
    environment.filters['join_to'] = join_to
    return environment


def _create_loader(loaders=None):
    if loaders is None:
        loaders = [
            jinja2.FileSystemLoader('.'),
        ]

    return jinja2.ChoiceLoader(loaders)


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
        config = {'md_extensions': ['jinja2.ext.do']}
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
            output_string = render_template_to_file(config, template_name, context)
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

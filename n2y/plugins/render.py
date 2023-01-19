import re
import uuid
import logging
import collections
from importlib import import_module

import jinja2
import pandoc
from jinja2.environment import TemplateStream
from pandoc.types import RawBlock, Format, CodeBlock


from n2y.blocks import FencedCodeBlock
from n2y.errors import UseNextClass


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


def render_template_to_file(config, template_markdown, context, output_file, loaders=None):
    generator = generate_template_output(config, template_markdown, context, loaders=loaders)
    TemplateStream(generator).dump(output_file)


# def render_template_to_string(config, template_filename, context, loaders=None):
#     return ''.join(generate_template_output(config, template_filename, context, loaders=loaders))


def generate_template_output(config, template_markdown, context, loaders=None):
    environment = _create_jinja_environment(config, loaders)
    first_pass_output = FirstPassOutput()
    environment.globals['first_pass_output'] = first_pass_output
    output_line_list = generate_template_output_lines(environment, template_markdown, context)
    if first_pass_output.second_pass_is_requested:
        jinja2.clear_caches()
        first_pass_output_filled = FirstPassOutput(output_line_list)
        second_pass_environment = _create_jinja_environment(config, loaders)
        second_pass_environment.globals['first_pass_output'] = first_pass_output_filled
        output_line_list = generate_template_output_lines(second_pass_environment, template_markdown, context)
    return (line for line in output_line_list)


def generate_template_output_lines(environment, template_markdown, context):
    source_line_list = _generate_source_line_list(template_markdown, context)
    return [line for line in _generate_output_lines(environment, source_line_list)]


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


def _generate_source_line_list(template, context):
    generator = template.generate(**context)
    source = ''.join(generator)
    # template generator usually loses trailing new line.
    if source and source[-1] != '\n':
        source += '\n'
    return source.splitlines(keepends=True)


def _generate_output_lines(environment, source_line_list):
    output_generator = (line for line in source_line_list)
    post_process_filters = post_processing_filter_list(environment)
    for post_process_filter in post_process_filters:
        output_generator = (x for x in post_process_filter(output_generator))
    return output_generator


class RawFencedCodeBlock(FencedCodeBlock):
    """
    Adds support for raw codeblocks.

    Any code block whose caption begins with "{=language}" will be made into a
    raw block for pandoc to parse. This is useful if you need to drop into Raw
    HTML or other formats.

    See https://pandoc.org/MANUAL.html#generic-raw-attribute
    """
    trigger_regex = re.compile(r'^\{template\}')

    def __init__(self, client, notion_data, page, get_children=True):
        super().__init__(client, notion_data, page, get_children)
        result = self.caption.matches(self.trigger_regex)
        if not result or self.client.render_config == None:
            raise UseNextClass()
        if self.client.render_config is None:
            raise NotImplementedError(
                'The "render-config" argument must be set to use the "render" plugin'
            )

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
        return self._render(CodeBlock(('', language, []), self.rich_text.to_plain_text()))
    
    def _render(self, ast):
        markdown = pandoc.write(ast)
        context = self.client.context_from_yaml_cache()
        config = self.client.render_config
        tempfile_name = f'{str(uuid.uuid4())}.md'
        tempfile = open(tempfile_name, 'x')
        tempfile.close()
        render_template_to_file(config, markdown, context, tempfile_name)
        with open(tempfile_name, 'r') as file:
            ast = pandoc.read(file.read())
        return ast



notion_classes = {
    "blocks": {
        "code": RawFencedCodeBlock,
    }
}
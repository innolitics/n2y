import re
import yaml
import jinja2
import collections
from jinja2 import FunctionLoader

try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader

from n2y.plugins.render import generate_template_output


# Some end-to-end tests are run against a throw-away Notion account with a few
# pre-written pages. Since this is a throw-away account, we're fine including
# the auth_token in the codebase. The login for this throw-away account is in
# the Innolitics' 1password "Everyone" vault. If new test pages are added, this
# will need to be used to create them.
NOTION_ACCESS_TOKEN = 'secret_lylx4iL5awveY3re6opuvSQqM6sMRu572TowhfzPy5r'
# see https://pandoc.org/MANUAL.html#exit-codes
PANDOC_PARSE_ERROR = 64

yaml_frontmatter_regexp = re.compile(r'^---$(.*)^---$', re.MULTILINE | re.DOTALL)

block_colors = {
    "default",
    "gray",
    "brown",
    "orange",
    "yellow",
    "green",
    "blue",
    "purple",
    "pink",
    "red",
    "gray_background",
    "brown_background",
    "orange_background",
    "yellow_background",
    "green_background",
    "blue_background",
    "purple_background",
    "pink_background",
    "red_background",
}


def parse_yaml_front_matter(content):
    match = yaml_frontmatter_regexp.match(content)
    if match:
        yaml_front_matter_str = match.group(1)
        return yaml.load(yaml_front_matter_str, Loader=Loader)
    else:
        raise ValueError("No YAML front matter found")


def newline_lf(input):
    return input.replace('\r\n', '\n')


def render_from_string(
    input_string=None,
    context=None,
    config=None,
    template_name=None,
    input_dictionary=None
):
    jinja2.clear_caches()
    if config is None:
        config = {}
    if template_name is None:
        template_name = 'input.md'
    if input_dictionary is None:
        input_dictionary = {}
    if input_string is not None:
        input_dictionary[template_name] = input_string
    if context is None:
        context = {}

    def load_string(template_name):
        return input_dictionary[template_name]

    loaders = [FunctionLoader(load_string)]

    return render_template_to_string(config, template_name, context, loaders=loaders)


def render_template_to_string(config, template_filename, context, loaders=None):
    return ''.join(generate_template_output(config, template_filename, context, loaders=loaders))


def invert_dependencies(objects, id_key, dependencies_key):
    # TODO: add docstring
    inverted = collections.defaultdict(lambda: set())
    for o in objects:
        for d in o[dependencies_key]:
            inverted[d].add(o[id_key])
    inverted_as_list = list(inverted.items())
    return sorted(inverted_as_list, key=lambda i: i[0].split('-'))

import re

import yaml
try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader

# This is not a security risk because the integration token that provides
# read-only access to public notion pages in a throw-away notion account.
NOTION_ACCESS_TOKEN = 'secret_lylx4iL5awveY3re6opuvSQqM6sMRu572TowhfzPy5r'


yaml_frontmatter_regexp = re.compile(r'^---$(.*)^---$', re.MULTILINE | re.DOTALL)


def parse_yaml_front_matter(content):
    match = yaml_frontmatter_regexp.match(content)
    if match:
        yaml_front_matter_str = match.group(1)
        return yaml.load(yaml_front_matter_str, Loader=Loader)
    else:
        raise ValueError("No YAML front matter found")

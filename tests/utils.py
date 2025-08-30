import re
import yaml

try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader


# Some end-to-end tests are run against a throw-away Notion account with a few
# pre-written pages. Since this is a throw-away account, we're fine including
# the auth_token in the codebase. The login for this throw-away account is in
# the Innolitics' 1password "Everyone" vault. If new test pages are added, this
# will need to be used to create them.
NOTION_ACCESS_TOKEN = "secret_lylx4iL5awveY3re6opuvSQqM6sMRu572TowhfzPy5r"
# see https://pandoc.org/MANUAL.html#exit-codes
PANDOC_PARSE_ERROR = 64

yaml_frontmatter_regexp = re.compile(r"^---$(.*)^---$", re.MULTILINE | re.DOTALL)

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
    # Windows uses \r\n (carriage return + newline) for line breaks.
    # Linux/macOS and Pandoc use only \n.
    # If your tests compare strings like Markdown output, and Pandoc always produces \n,
    # then your Windows-generated strings with \r\n would fail the equality check.
    return input.replace("\r\n", "\n")

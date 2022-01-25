# Notion to YAML

This commandline tool pulls data from Notion into YAML and markdown.

## Installation

```
pip install n2y
```

## Authorization

In notion, go to the "Settings and Members" page. If you're an admin, you should see an "Integrations" option in the side bar. Click the link that says "Develop your own integrations" and follow the instructions on the page. Copy the "Internal Integration Token" into the `NOTION_ACCESS_TOKEN` environment variable.

Finally, in Notion you'll need to share the relevant pages with your internal integration---just like you'd share a page with another person.

## Converting a Database to YAML

Copy the link for the database you'd like to export to YAML. Note that linked databases aren't supported. Then run:

```
n2y DATABASE_LINK > database.yml
```

By default, `n2y` will simplify the JSON blobs returned by Notion. You can dump the raw data using the `--raw` argument.

## Plugins

The default implementation can be extended or replaced with plugins. To specify a plugin add `--plugins path_to_plugin.py` as a command line argument.

**Example plugin file:**

``` python
from n2y.converter import ParagraphBlock


class ParagraphBlockOverride(ParagraphBlock):
    def to_pandoc(self):
        # Add custom code here. Call super().to_pandoc() to get default implementation.
        return super().to_pandoc()

# Add classes to override here 
exports = {
    'ParagraphBlock': ParagraphBlockOverride
}
```

Classes that can be extended (case sensitive):

- ParagraphBlock
- ChildPageBlock
- HeadingOne
- HeadingTwo
- HeadingThree
- Divider
- Bookmark
- ImageBlock
- CodeBlockFenced
- Quote

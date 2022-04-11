# Notion to YAML

This commandline tool pulls data from Notion into YAML and markdown.

We use it at [Innolitics](https://innolitics.com) to generate pages in our website using Notion as a content management system.

The goal of the project is to provide a flexible way to export data from Notion into various text formats since Notion's built in Markdown and CSV export options are limited. For example, they don't preserve colors, underlining, and various types of blocks that are present in Notion.

We've evaluated tools like [Super.so](https://super.so), which also let you use Notion as a CMS, but none of them provide enough flexibility for our needs.

## Installation

```
pip install n2y
```

Install [pandoc](https://github.com/jgm/pandoc/releases/) for your operating system. (Tested with version 2.16.2)

## Authorization

In notion, go to the "Settings and Members" page. If you're an admin, you should see an "Integrations" option in the side bar. Click the link that says "Develop your own integrations" and follow the instructions on the page. Copy the "Internal Integration Token" into the `NOTION_ACCESS_TOKEN` environment variable.

Finally, in Notion you'll need to share the relevant pages with your internal integration---just like you'd share a page with another person.

## Converting a Database to YAML

Copy the link for the database you'd like to export to YAML. Note that linked databases aren't supported. Then run:

```
n2y DATABASE_LINK > database.yml
```

## Converting a Database to markdown files

```
n2y -o markdown DATABASE_LINK
```

This process will automatically skip empty pages, pages with duplicate names, and untitled pages.

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

- Bookmark
- BulletedList
- BulletedListItem
- ChildPageBlock
- CodeBlockFenced
- Divider
- HeadingOne
- HeadingTwo
- HeadingThree
- ImageBlock
- NumberedList
- NumberedListItem
- ParagraphBlock
- Quote
- EquationBlock
- RowBlock
- TableBlock
- ToDo
- ToDoItem
- Toggle

## Releases

Any git commit tagged with a string starting with "v" will automatically be pushed to pypi.

Before pushing such commits, be sure to update the change log below.

## Changelog

### v0.2.2

- Improve logging, including adding arguments to control the verbosity of the output.
- Fix bug that occurs if Notion has bolded, italic or struckthrough text that includes a space on the ends. When this occured, the generated markdown would not work properly. For example, bolded text could end up producing a list.
- Ignore the name column argument when generating YAML.

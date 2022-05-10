# Notion to YAML

This commandline tool exports data from selected Notion pages and databases into YAML and markdown files. Internally, it converts the Notion pages into a [Pandoc](https://pandoc.org) AST, which enables fine-grained customization of the conversion process.

We use it at [Innolitics](https://innolitics.com) to generate pages for our website, thus allowing us to use Notion as a content management system. We also use it to generate PDFs and Word Documents from Notion pages.

## Installation

To install the tool, just run:

```
pip install n2y
```

You'll also need to install [pandoc](https://github.com/jgm/pandoc/releases/). We've tested against version 2.16.2, but any newer versions should work too.

## Authorization

Before you'll be able to export any content from your Notion account you'll first need to give n2y permission to access the pages. You'll need to be an admin.

To do this, go to the "Settings and Members" page in Notion. You should see an "Integrations" option in the side bar. Click the link that says "Develop your own integrations" and follow the instructions on the page. Copy the "Internal Integration Token" into the `NOTION_ACCESS_TOKEN` environment variable.

Finally, in Notion you'll need to share the relevant pages with your internal integration---just like you'd share a page with another person.

## Example Usage

### Convert a Database to YAML

Copy the link for the database you'd like to export to YAML. Note that linked databases aren't supported. Then run:

```
n2y DATABASE_LINK > database.yml
```

### Convert a Database to a set of Markdown Files

```
n2y -f markdown DATABASE_LINK
```

This process will automatically skip untitled pages or pages with duplicate names.

### Convert a Page to a Markdown File

If the page is in a database, then it's properties will be included in the YAML front matter. If the page is not in a database, then the title of the page will be included in the YAML front matter.

```
n2y -f markdown PAGE_LINK
```

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

### v0.2.4

- Add support for exporting pages
- Add basic support for links

### v0.2.3

- Skip Notion pages with falsey names.
- Create shortcut flags for each parser arguement.

### v0.2.2

- Improve logging, including adding arguments to control the verbosity of the output.
- Fix bug that occurs if Notion has bolded, italic or struckthrough text that includes a space on the ends. When this occured, the generated markdown would not work properly. For example, bolded text could end up producing a list.
- Ignore the name column argument when generating YAML.
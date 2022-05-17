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
n2y PAGE_LINK > page.md
```

## Plugins

At the core of n2y are a set of python classes that subclass the `Block` class. These classes are responsible for converting the Notion data into pandoc abstract syntax tree objects. We use a python wrapper library that makes it easier to work with pandoc's AST. See [here](https://boisgera.github.io/pandoc/document/) for details. See the [Notion API documentation](https://developers.notion.com/reference/block) for details about their data structures.

The default implementation of these block classes can be modified using a plugin system. To create a plugin, follow these steps:

1. Create a new Python file.
2. Subclass the various Block classes and modify the `to_pandoc` methods as desired
3. Run n2y with the `--plugins` argument pointing to your python module.

### Example Plugin File

```python
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

### Default Block Class's

Here are the default block classes that can be extended:

| Class Name | Noteworthy Behavior |
| --- | --- |
| BookmarkBlock | |
| BulletedListItemBlock | |
| CalloutBlock | The content of the callout block is extracted, but the emoji and background color are ignored. |
| ChildPageBlock | |
| FencedCodeBlock | |
| DividerBlock | |
| HeadingOneBlock | |
| HeadingTwoBlock | |
| HeadingThreeBlock | |
| ImageBlock | It uses the URL for external images, but downloads uploaded images to the `MEDIA_ROOT` and replaces the path with a relative url based off of `MEDIA_URL`. The "caption" is used for the alt text. |
| NumberedListItemBlock | |
| ParagraphBlock | |
| QuoteBlock | |
| EquationBlock | Converted to "display math" using LaTeX; see the [pandoc](https://pandoc.org/MANUAL.html#math) documentation. |
| TableBlock | |
| RowBlock | |
| ToDoItemBlock | |
| ToggleBlock | Convert the toggles into a bulleted list. |

Most of the Notion blocks can generate their pandoc AST from _only_ their own data. The one exception is the list item blocks; pandoc, unlike Notion, has an encompassing node in the AST for the entire list. The `ListItemBlock.list_to_pandoc` class method is responsible for generating this top-level node.

## Architecture

N2y's architecture is divided into four main steps:

1. Configuration
2. Retrieve data from Notion (by instantiating the `Block` instances)
3. Convert to the pandoc AST (by calling `block.to_pandoc()`)
4. Writing the pandoc AST into markdown or YAML

## Releases

Any git commit tagged with a string starting with "v" will automatically be pushed to pypi.

Before pushing such commits, be sure to update the change log below.

## Roadmap

Here are some features we're planning to add in the future:

- Add support for all block types and database property types
- Add support for exporting sets of related databases
- Make the plugin system more fully featured and easier to use
- Add support for recursively dumping sets of pages and preserving links between them
- Add some sort of Notion API cacheing mechanism
- Add more examples to the documentation
- Make it so that plugins and other configuration can be set for only a sub-set
  of the exported pages, that way multiple configurations can be applied in a
  single export

## Changelog

### v0.2.4

- Add support for exporting pages
- Add basic support for links
- Add support for callout blocks

### v0.2.3

- Skip Notion pages with falsey names.
- Create shortcut flags for each parser arguement.

### v0.2.2

- Improve logging, including adding arguments to control the verbosity of the output.
- Fix bug that occurs if Notion has bolded, italic or struckthrough text that includes a space on the ends. When this occured, the generated markdown would not work properly. For example, bolded text could end up producing a list.
- Ignore the name column argument when generating YAML.

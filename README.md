# Notion to YAML

[![Test](https://github.com/innolitics/n2y/actions/workflows/tests.yml/badge.svg)](https://github.com/innolitics/n2y/actions/workflows/tests.yml)

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

At the core of n2y are a set of python classes that represent the various parts of a Notion workspace:

| Notion Object Type | Description |
| --- | --- |
| Page | Represents a Notion page (which may or may not be in a database) |
| Database | A Notion database, which can also be though of as a set of Notion pages with some structured meta data, or properties |
| Property | A type descriptor for a property (or column) in a Notion database |
| PropertyValue | A particular value that a particular page in database has for a particular Property |
| Block | A bit of content within a Page |
| RichTextArray | A sequence of formatted text in Notion; present in many blocks and property values |
| RichText | A segment of text with the same styling |
| Mention | A reference to another Notion object (e.g., a page, database, block, user, etc. )
| User | A notion user; used in property values and in page, block, and database metadata |
| File | A file |

The `Property`, `PropertyValue`, `Block`, `RichText`, and `Mention` classes have subclasses that represent the various subtypes. E.g., there is a `ParagraphBlock` that represents paragraph.

These classes are responsible for converting the Notion data into pandoc abstract syntax tree objects. We use a python wrapper library that makes it easier to work with pandoc's AST. See [here](https://boisgera.github.io/pandoc/document/) for details. See the [Notion API documentation](https://developers.notion.com/reference/block) for details about their data structures.

The default implementation of these classes can be modified using a plugin system. To create a plugin, follow these steps:

1. Create a new Python module
2. Subclass the various notion classes, modifying their constructor or `to_pandoc` method as desired
3. Run n2y with the `--plugin` argument pointing to your python module

See the [builtin plugins](https://github.com/innolitics/n2y/tree/rich-text-extensions/n2y/plugins) for examples.

### Using Multiple Plugins

You can use multiple plugins. If two plugins provide classes for the same notion object, then the last one that was loaded will be instantiated.

Often you'll want to use a different class only in certain situations. For example, you may want to use a different Page class with its own unique behavior only for pages in a particular database.

If your plugin class raise the `n2y.errors.UseNextClass` exception in its constructor, then n2y will move on to the next class (which may be the builtin class if only one plugin was used).

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
| FileBlock | Acts the same way as the ImageBlock, except that in the documents it only ever shows the URL. |
| NumberedListItemBlock | |
| ParagraphBlock | |
| QuoteBlock | |
| EquationBlock | Converted to "display math" using LaTeX; see the [pandoc](https://pandoc.org/MANUAL.html#math) documentation. |
| TableBlock | |
| RowBlock | |
| ToDoItemBlock | |
| ToggleBlock | Convert the toggles into a bulleted list. |

Most of the Notion blocks can generate their pandoc AST from _only_ their own data. The one exception is the list item blocks; pandoc, unlike Notion, has an encompassing node in the AST for the entire list. The `ListItemBlock.list_to_pandoc` class method is responsible for generating this top-level node.

## Built-in Plugins

N2y provides a few builtin plugins. Brief descriptions are provided below, but see [the code](https://github.com/innolitics/n2y/tree/rich-text-extensions/n2y/plugins) for details.

### Deep Headers

Notion only support three levels of headers, but sometimes this is not enough. This plugin enables support for h4 and h5 headers in the documents exported from Notion. Any Notion h3 whose text begins with the characters "= " is converted to an h4, and any h3 that begins with "== " is converted to an h5, and so on.

### Remove Callouts

Completely remove all callout blocks. It's often helpful to include help text in callout blocks, but usually this help text should be stripped out of the final generated documents.

### Raw Fenced Code Blocks

Any code block whose caption begins with "{=language}" will be made into a raw block for pandoc to parse. This is useful if you need to drop into Raw HTML or other formats. See [the pandoc documentation](https://pandoc.org/MANUAL.html#generic-raw-attribute) for more details on the raw code blocks.

### Mermaid Fenced Code Blocks

Adds support for generating mermaid diagrams from codeblocks with the "mermaid" language, as supported in the Notion UI.

This plugin assumes that the `mmdc` mermaid commandline tool is available, and will throw an exception if it is not.

If there are errors with the mermaid syntax, it is treated as a normal codeblock and the warning is logged.

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

- Add support for all block types
- Make the plugin system more fully featured and easier to use
- Add support for recursively dumping sets of pages and preserving links between them
- Add some sort of Notion API caching mechanism
- Add more examples to the documentation
- Make it so that plugins and other configuration can be set for only a sub-set
  of the exported pages, that way multiple configurations can be applied in a
  single export

## Changelog

### v0.4.2

- Sanitize filenames (so that a notion page called "HFE/UE Report" won't attempt to create a directory.
- Remove styling that is tracked in Notion but is not visible in their UI, so as
  to avoid generating confusing output. In particular, remove styling from page
  titles and bolding for header blocks.
- Ignore (and print warnings and links) if there are unsupported blocks.
- Fix issue where images with the same name would collide with each other
- Add a mermaid diagram plugin
- Make page and database mentions more efficient; fix bug related to circular references with page mentions
- Fix pagination bug that occurred with databases with more than 100 pages
- Make it easier to use multiple plugins for the same class by adding the "UseNextClass" exception
- Add the ability to include notion ids in export YAML files using the `id_property` commandline argument
- Add support for the SyncedBlock
- Add support for filtering and sorting databases using the `--database-config` property

### v0.4.1

- Add the ability to customize the where database page content is stored
  (including providing the option not to export the content).
- Add support for the FileBlock
- Add `n2y.plugins.removecallouts` plugin
- Fix a bug that would occur if you had nested paragraphs or callout blocks
- Drop Notion code highlighting language if its not supported
- Ignore table of contents, breadcrumb, template, and unsupported blocks

### v0.4.0

- Split out the various rich_text and mention types into their own classes
- Add plugin support for all notion classes
- Improve error handling when the pandoc conversion fails
- Add a builtin "deep header" plugin which makes it possible to use h4 and h5
  headers in Notion

### v0.3.0

- Add support for exporting sets of linked YAML files
- Extend support to all property value types (including rollupws, etc.)
- Removed the "name_column" option (will be replaced with better natural key handling)

### v0.2.4

- Add support for exporting pages
- Add basic support for links
- Add support for callout blocks

### v0.2.3

- Skip Notion pages with falsey names.
- Create shortcut flags for each parser argument.

### v0.2.2

- Improve logging, including adding arguments to control the verbosity of the output.
- Fix bug that occurs if Notion has bolded, italic or struckthrough text that includes a space on the ends. When this occurred, the generated markdown would not work properly. For example, bolded text could end up producing a list.
- Ignore the name column argument when generating YAML.

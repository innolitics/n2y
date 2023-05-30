# Notion to YAML

[![Test](https://github.com/innolitics/n2y/actions/workflows/tests.yml/badge.svg)](https://github.com/innolitics/n2y/actions/workflows/tests.yml)

This commandline tool exports data from selected Notion pages and databases into YAML and markdown files. Internally, it converts the Notion pages into a [Pandoc](https://pandoc.org) AST, which enables fine-grained customization of the conversion process.

We use it at [Innolitics](https://innolitics.com) to generate pages for our website, thus allowing us to use Notion as a content management system. We also use it to generate PDFs and Word Documents from Notion pages.

## Installation

Install first `pandoc` and `mermaid` CLIs. Please note that `n2y` has only been tested with `pandoc 2.19.2` and `mermaid-cli 9.4.0`. This [pandoc](https://github.com/jgm/pandoc/releases/tag/2.19.2) link will take you to their `2.19.2` github releases page. This [mermaid](https://github.com/mermaid-js/mermaid-cli) link will take you to their github page where you will find installation instructions. If using `npm` to install `mermaid`, append `@9.4.0` to the `npm` command to install that specific version.

Finally, install `n2y`:

```
pip install n2y
```

## Authorization

Before you'll be able to export any content from your Notion account you'll first need to give n2y permission to access the pages. You'll need to be an admin.

To do this, go to the "Settings and Members" page in Notion. You should see an "Integrations" option in the side bar. Click the link that says "Develop your own integrations" and follow the instructions on the page. Copy the "Internal Integration Token" into the `NOTION_ACCESS_TOKEN` environment variable.

Finally, in Notion you'll need to share the relevant pages with your internal integration---just like you'd share a page with another person.

## Configuration

N2y is configured using a single YAML file. This file contains a few top-level keys:

| Top-level key | Description |
| --- | --- |
| media_url | Sets the base URL for all downloaded media files (e.g., images, videos, PDFs, etc.) |
| media_root | The directory where media files should be downloaded to |
| exports | A list of export configuration items, indicating how a notion page or database is to be exported. See below for the keys.  |
| export_defaults | Default values for the export configuration items. |

The export configuration items may contain the following keys:

| Export key | Description |
| --- | --- |
| id | The notion database or page id, taken from the "share URL". |
| node_type | Either "database_as_yaml", "database_as_files", or "page". |
| output | The path the output file, or directory, where the data will be written. |
| pandoc_format | The [pandoc format](https://pandoc.org/MANUAL.html#general-options) that we're generating. |
| pandoc_options | A list of strings that are [writer options](https://pandoc.org/MANUAL.html#general-writer-options) for pandoc. |
| content_property | When set, it indicates the property name that will contain the content of the notion pages in that databse. If set to `None`, then only the page's properties will be included in the export. (Only applies to the `database_as_files` node type.) |
| yaml_front_matter | Only used when exporting to text files. Indicates if the page properties should be exported as yaml front matter. |
| id_property | When set, this indicates the property name in which to place the page's underlying notion ID. |
| url_property | When set, this indicates the property name in which to place the page's underlying notion url. |
| filename_template | This key is only used for the "database_as_files" node type; when set, it provides a [format string](https://docs.python.org/3/library/string.html#formatstrings) that is evaluated against the page's properties to generate the file name. Note that the filenames are sanitized. When not set, the title property is used and the extension is deduced from the `pandoc_format`. A special "TITLE" property may be used to access the title property in the template string. |
| plugins | A list of python modules to use as plugins. |
| notion_filter | A [notion filter object](https://developers.notion.com/reference/post-database-query-filter) to be applied to the database. |
| notion_sorts | A [notion sorts object](https://developers.notion.com/reference/post-database-query-sort) to be applied to the database. |
| property_map | A mapping between the name of properties in Notion, and the name of the properties in the exported files. |

## Example Configuration Files

The command is run using `n2y configuration.yaml`.

### Convert a Database to YAML

A notion database (e.g., with a share URL like this https://www.notion.so/176fa24d4b7f4256877e60a1035b45a4?v=130ffd3224fd4512871bb45dbceaa7b2) could be exported into a YAML file using this minimal configuration file:

```
exports:
- id: 176fa24d4b7f4256877e60a1035b45a4
  node_type: database_as_yaml
  output: database.yml
```

### Convert a Database to a set of Markdown Files

The same database could be exported into a set of markdown files as follows:

```
exports:
- id: 176fa24d4b7f4256877e60a1035b45a4
  node_type: database_as_files
  output: directory
  filename_template: "{Name}.md"
```

Each page in the database will generate a single markdown file, named according to the `filename_template`. This process will automatically skip pages whose "Name" property is empty.

### Convert a Page to a Markdown File

An individual notion page (e.g., with a share URL like this https://www.notion.so/All-Blocks-Test-Page-5f18c7d7eda44986ae7d938a12817cc0) could be exported to markdown with this minimal configuration file:

```
exports:
- id: 5f18c7d7eda44986ae7d938a12817cc0
  node_type: page
  output: page.md
```

### Audit a Page and it's Children For External Links

Sometimes it is useful to ensure that a root Notion page, and it's child-pages, don't contain links to any notion pages outside the hierarchy. The `n2yaudit` tool can be used to audit a page hierarchy for any of these links.

```
n2yaudit PAGE_LINK
```

### Bigger Example

This example shows how you can use the `export_defaults` property to avoid duplicated configuration between export items. It also shows now you can use notion filters to export pages from the same database into two different directories.

```
media_root: "media"
media_url: "./media/"
export_defaults:
  plugins:
    - "n2y.plugins.mermaid"
    - "n2y.plugins.rawcodeblocks"
    - "n2y.plugins.removecallouts"
    - "n2y.plugins.deepheaders"
    - "n2y.plugins.expandlinktopages"
  content_property: null
  id_property: id
  url_property: url
exports:
  - output: "documents/dhf"
    node_type: "database_as_files"
    filename_template: "{Name}.md"
    id: e24f839e724848d69342d43c07cb5f3e
    plugins:
      - "n2y.plugins.mermaid"
      - "n2y.plugins.rawcodeblocks"
      - "n2y.plugins.removecallouts"
      - "n2y.plugins.deepheaders"
      - "n2y.plugins.expandlinktopages"
      - "plugins.page"
      - "plugins.idmentions"
    notion_filter:
      property: "Tags"
      multi_select: { "contains": "DHF" }
  - output: "documents/510k"
    id: e24f839e724848d69342d43c07cb5f3e
    filename_template: "{Name}.md"
    node_type: "database_as_files"
    plugins:
      - "n2y.plugins.mermaid"
      - "n2y.plugins.rawcodeblocks"
      - "n2y.plugins.removecallouts"
      - "n2y.plugins.deepheaders"
      - "n2y.plugins.expandlinktopages"
      - "plugins.page"
      - "plugins.idmentions"
    notion_filter:
      property: "Tags"
      multi_select: { "contains": "510(k)" }
  - output: "data/Roles.yml"
    id: b47a694953714222810152736d9dc66c
    node_type: "database_as_yaml"
    content_property: "Description"
  - output: "data/Glossary.yml"
    id: df6bef74e2372118becd93e321de2c69
    node_type: "database_as_yaml"
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
| Emoji | An emoji |

The `Property`, `PropertyValue`, `Block`, `RichText`, and `Mention` classes have subclasses that represent the various subtypes. E.g., there is a `ParagraphBlock` that represents paragraph.

These classes are responsible for converting the Notion data into pandoc abstract syntax tree objects. We use a python wrapper library that makes it easier to work with pandoc's AST. See [here](https://boisgera.github.io/pandoc/document/) for details. See the [Notion API documentation](https://developers.notion.com/reference/block) for details about their data structures.

The default implementation of these classes can be modified using a plugin system. To create a plugin, follow these steps:

1. Create a new Python module
2. Subclass the various notion classes, modifying their constructor or `to_pandoc` method as desired
3. Set the `plugins` property in your export config to the module name (e.g., `n2y.plugins.deepheaders`)

See the [builtin plugins](https://github.com/innolitics/n2y/tree/main/n2y/plugins) for examples.

### Using Multiple Plugins

You can use multiple plugins. If two plugins provide classes for the same notion object, then the last one that was loaded will be instantiated first.

Often you'll want to use a different class only in certain situations. For example, you may want to use a different Page class with its own unique behavior only for pages in a particular database. To accomplish this you can use the `n2y.errors.UseNextClass` exception. If your plugin class raise the `n2y.errors.UseNextClass` exception in its constructor, then n2y will move on to the next class (which may be the builtin class if only one plugin was used).

### Different Plugins for Different Exports

You may use different plugins for different export items, but keep in mind that the plugin module is imported only once. Also, if you export the same `Page` or `Database` multiple times with different plugins, due to an internal cache, the plugins that were enabled during the first run will be used.

### Default Block Class's

Here are the default block classes that can be extended:

| Class Name | Noteworthy Behavior |
| --- | --- |
| BookmarkBlock | Converts visual bookmark into plain text link in markdown, using the caption as the link text. |
| BreadcrumbBlock | These blocks are ignored |
| BulletedListItemBlock | |
| CalloutBlock | The content of the callout block is extracted, but the emoji and background color are ignored. |
| ChildDatabaseBlock | These blocks are ignored |
| ChildPageBlock | These blocks are ignored |
| ColumnBlock | |
| ColumnListBlock | Converts into a table where each column is such. |
| DividerBlock | |
| EmbedBlock | These blocks are ignored |
| EquationBlock | Converted to "display math" using LaTeX; see the [pandoc](https://pandoc.org/MANUAL.html#math) documentation. |
| FencedCodeBlock | |
| FileBlock | Acts the same way as the ImageBlock, except that in the documents it only ever shows the URL. |
| HeadingOneBlock | |
| HeadingTwoBlock | |
| HeadingThreeBlock | |
| ImageBlock | It uses the URL for external images, but downloads uploaded images to the `MEDIA_ROOT` and replaces the path with a relative url based off of `MEDIA_URL`. The "caption" is used for the alt text. |
| LinkToPageBlock | Transcribes the block into a plain text link |
| NumberedListItemBlock | |
| ParagraphBlock | |
| PdfBlock | Acts the same way as the Image block |
| QuoteBlock | |
| RowBlock | |
| SyncedBlock | Transcribe the contents of the synced block at the time it was constructed |
| TableBlock | |
| TableOfContentsBlock | These blocks are ignored |
| TemplateBlock | These blocks are ignored |
| ToDoItemBlock | |
| ToggleBlock | Convert the toggles into a bulleted list. |
| VideoBlock | Acts the same way as the Image block |

Most of the Notion blocks can generate their pandoc AST from _only_ their own data. The one exception is the list item blocks; pandoc, unlike Notion, has an encompassing node in the AST for the entire list. The `ListItemBlock.list_to_pandoc` class method is responsible for generating this top-level node.

## Built-in Plugins

N2y provides a few builtin plugins. These plugins are all turned off by default. Brief descriptions are provided below, but see [the code](https://github.com/innolitics/n2y/tree/main/n2y/plugins) for details.

### Jinja Render Page

CodeBlocks whose caption begins with "{jinja=pandocformat}" will be rendered using [Jinja](https://jinja.palletsprojects.com/en/3.1.x/templates/) into text and then read into the AST using the specified pandoc input format. Note that, other than the special "plain" format, the pandocformat must be available both for reading and writing.

Any databases that are [mentioned](https://www.notion.so/help/comments-mentions-and-reminders) in the codeblock's caption will be made available in the jinja render context within the `databases` dictionary.

Take the following code block for example:

```
<table>
  <tr><th>Name</th><th>Email</th></tr>
  {% for person in databases["People"] %}
  <tr><td>{{person.Name}}</td><td>{{person.Email}}</td></tr>
  {% endfor %}
</table>
```

The caption would be, "{jinja=html} @People," where "Name" and "Email" are properties in the "People" database.

Note that any rich text properties are rendered into the pandoc input format specified.

The codeblock's parent page's properties are made available in the `page` context variable.

The jinja context has a few special filters available to it:

| Name | Type | Description |
| --- | --- | --- |
| `join_to` | filter | Make it possible to join notion databases together. |
| `first_pass_output` | object | Makes it possible to access the full text of the initial page's render. Useful if you want to render a glossary of terms that are used on the page. |

See the [code](https://github.com/innolitics/n2y/blob/main/n2y/plugins/jinjarenderpage.py) for details.

### Deep Headers

Notion only support three levels of headers, but sometimes this is not enough. This plugin enables support for h4 and h5 headers in the documents exported from Notion. Any Notion h3 whose text begins with the characters "= " is converted to an h4, and any h3 that begins with "== " is converted to an h5, and so on.

### Remove Callouts

Completely remove all callout blocks. It's often helpful to include help text in callout blocks, but usually this help text should be stripped out of the final generated documents.

### Raw Fenced Code Blocks

Any code block whose caption begins with "{=pandocformat}" will be made into a raw block for pandoc to parse. This is useful if you need to drop into Raw HTML or other output formats that pandoc supports. See [the pandoc documentation](https://pandoc.org/MANUAL.html#generic-raw-attribute) for more details on the raw code blocks.

### Mermaid Fenced Code Blocks

Adds support for generating mermaid diagrams from codeblocks with the "mermaid" language, as supported in the Notion UI.

This plugin assumes that the `mmdc` mermaid commandline tool is available, and will throw an exception if it is not.

If there are errors with the mermaid syntax, it is treated as a normal codeblock and the warning is logged.

### Linked Header Blocks

Replace headers with links back to the originating notion block.

### Footnotes

Adds support for Pandoc-style footnotes. Any `text` rich texts that contain footnote references in the format `[^NUMBER]` (eg: `...some claim [^2].`) will be linked to the corresponding footnote paragraph block starting with `[NUMBER]:` (eg: `[2]: This is a footnote.`).

### DB Footnotes
Adds general footnote support (not specialized for markdown) with the expectation that all footnote content is placed in an inline database on the original page wherein footnote references are made. Specific footnote references are made with Notion's page mention feature, mentioning a specific footnote page in the database. For example, each page in the database can simply be titled with a footnote number and contain the footnote text as the page content. The inline database must have a title that ends with "Footnotes."

### Expand Link To Page Blocks

When this plugin is enabled, any "link to page" block (which can be created using the `/link` command in the Notion UI), will be replaced with the content of the page that is linked to. This makes it possible to use the "link to page" block to include repeated content in multiple locations. It is like a "synced content block" in this way, but unlike "synced content blocks" which don't play well when duplicating child pages, the "link to page" blocks can be duplicated more easily.

Note that any link to a page that the integration doesn't have access to will be skipped entirely (Notion returns an "Unsupported Block" in this case).

### Hidden Jinja Toggles

When this plugin is enabled, any "blue" colored toggle block will have it's children directly rendered. The text on the toggle itself will be ignored.

## Architecture

An n2y run is divided into four stages:

1. Loading the configuration (mostly in `config.py`)
2. Retrieve data from Notion (by instantiating various Notion object instances, e.g., `Page`, `Block`, `RichText`, etc.)
3. Convert to the pandoc AST (by calling `block.to_pandoc()`)
4. Writing the pandoc AST into one of the various output formats (mostly in `export.py`)

Every page object has a `parent` property, which may be a page, a database, or a workspace.

Every block has a `page` property which refers to the page that contains it.

Every rich text object and mention has a `block` property that is either refers
back to the block that contains it, or is None if the rich text is within a
property value or some other location.

## Cache

During development, it can be convenient to cache requests to Notion. This feature can be enabled by setting the `N2Y_CACHE` environment variable to the location of the sqlite file you'd like to use as your Notion request cache. To flush the cache, simply delete the file. Note that this feature is only available if you include dev options.

## Releases

Any git commit tagged with a string starting with "v" will automatically be pushed to pypi.

Be sure to update the [setup.py](https://github.com/innolitics/n2y/blob/main/setup.py#L14) version number first.

You can create the tag using, e.g., `git tag v0.3.4` and you can push it using `git push && git push --tags`.

Before pushing such commits, be sure to update the change log below.

## Contributing

To work on the repository, clone the git repo. From within the repo (and ideally within a python virtual environment), install `n2y` from the local copy, including the dev dependencies:

```
pip install -e '.[dev]'
```

You can then run the tests and the linter as follows:

```
flake8 .
pytest tests
```

## Developer Tools

### Pandoc

`n2y` is built on top of [`pandoc`](https://pandoc.org/MANUAL.html), using it to build intermediate representations and for output generation. Being familiar with the pandoc AST is important as an `n2y` developer. Documentation is available for the [native Haskell AST](https://hackage.haskell.org/package/pandoc-types-1.23) and for the corresponding [Python wrapper library](https://boisgera.github.io/pandoc/document/) used directly by `n2y`.

As part of a typical development cycle, you can use the `pandoc` CLI to inspect the relationship between, for example, GitHub-flavored Markdown and the native `pandoc` AST. The following CLI invocation of `pandoc` takes in the GitHub-flavored Markdown file "example.md", converts it to the `pandoc` AST in JSON format, and pipes this output to the command line `jq` JSON processor program for viewing in the terminal:

```
pandoc -f gfm -t json example.md | jq .
```

The following command performs a full round-trip from GitHub-flavored Markdown to the `pandoc` AST and back to GitHub-flavored Markdown:

```
pandoc -f gfm -t json example.md | pandoc -f json -t gfm
```

## Roadmap

Here are some features we're planning to add in the future:

- Make the plugin system more fully featured and easier to use
- Add support for recursively dumping sets of pages and preserving links between them
- Add some sort of Notion API caching mechanism
- Add more examples to the documentation

## Changelog

### v0.9.0

- Replace the `filename_property` configuration option with the more generic `filename_template`.
- Make it so we can render pages into any pandoc format
- Include properties as pandoc meta values
- Add export config option to indicate if we should export YAML front matter

### v0.8.0

- Add requests cache to speed up dev loop
- Update `jinjarenderpage` so that it no pulls databases mentioned in the
  caption, instead of relying on the exports list. Also, make the
  jinjacodeblocks support any pandoc format.
- Make it so that we can render property values into any pandoc format

### v0.7.5

- Flatten Column List Blocks
- Add `jinjarenderpage` plugin to render jinja in code blocks

### v0.7.4

- Add features that allow the notion Client to retry api calls after being rate limited.

### v0.7.3

- Fix bug by filtering LineBreak class from table cells.

### v0.7.2

- Fix bug in mermaid by fixing error image file path.

### v0.7.1

- Handle graphical syntax errors in mermaid plugin and update end to end test.

### v0.7.0

- Fix bug by adding block id to save file function in mermaid plugin and getting tests to pass.

### v0.6.9

- Fix bug by naming files by the block id instead of the page id.

### v0.6.8

- Fix bug by conditionally deleting the id property of property types when copying database children.

### v0.6.7

- Fix appension bug by replacing skipped child_page and child_database blocks with empty dictionaries in the list returned by `Client.append_child_notion_blocks()`

### v0.6.6

- add `get_children()` method to databases and pages in order to update `Database._children` and `Page._children` manually
- add `Client.copy_notion_database_children()` which allows users to copy a list of children (pages) into another database
- correct `Client.append_child_notion_blocks()` (it now copies database children the appended child_databases)

### v0.6.5

- Fix bug by deleting superfluous print statements

### v0.6.4

- Update how database filters children
- Add version flag

### v0.6.3

- Initiate the n2y.plugins module (somewhere along the line, the `init.py` file must have been deleted).

### v0.6.2

- The `Client.append_child_notion_blocks()` had a typo that is now fixed. It also limits the amount of children sent into the Notion API to be appended to 100 at a time, per their parameters

### v0.6.1

- Get_children is now a method in the `Block` class to allow for the updating of children lists after children have been appended.
- Append_child_notion_blocks can now handle the appension of `child_page` and `child_database` block types.
- The original notion_data used to save `Block` class objects is now stored by them in the `Block.notion_data` attribute and what used to be stored there (the notion type data) is now stored in a property called `Block.notion_type_data`

### v0.6.0

- The export is now configured using a single YAML file instead of the growing list of commandline arguments. Using a configuration file allows multiple page and database exports to be made in a single run, which in turn improves caching and will enable future improvements, like preserving links between generated HTML or markdown pages.
- Added the `pandoc_format` and `pandoc_options` fields, making it possible to output to any format that pandoc supports.
- Removed the ability to export a set of related databases (this is less useful now that we have a configuration file).
- Add support for remapping property names in the exports using the `property_map` option
- Add basic support for emoji icons for pages.

### v0.5.0

- Add support for dumping the notion urls using `--url-property`.
- Add support for all types of rollups (including arrays of other values)
- Add plugin for creating headers that link back to the notion blocks
- Add a property to rich text arrays, rich text, and mention instances back to the block they're contained in IF they happen to be contained in a block (some rich text arrays, etc. are from property values). This is useful when developing plugins.
- Add `n2y.plugins.footnotes` plugin
- Add support for exporting HTML files (useful for generating jekyll pages or if you need pandoc features that aren't supported in github flavored markdown).
- Added the `n2yaudit` tool.
- Add the "link to page block"
- Added support for the column block types.
- Added basic support the link to page block type.

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
- Add support for ColumnBlock and ColumnListBlock

### v0.4.1

- Add the ability to customize the where database page content is stored
  (including providing the option not to export the content).
- Add support for the FileBlock
- Add `n2y.plugins.removecallouts` plugin
- Fix a bug that would occur if you had nested paragraphs or callout blocks
- Drop Notion code highlighting language if its not supported
- Ignore table of contents, breadcrumb, template, and unsupported blocks

### v0.4.0

- Split out the various rich\_text and mention types into their own classes
- Add plugin support for all notion classes
- Improve error handling when the pandoc conversion fails
- Add a builtin "deep header" plugin which makes it possible to use h4 and h5
  headers in Notion

### v0.3.0

- Add support for exporting sets of linked YAML files
- Extend support to all property value types (including rollupws, etc.)
- Removed the "name\_column" option (will be replaced with better natural key handling)

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

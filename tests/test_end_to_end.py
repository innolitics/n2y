import logging
import os
from os import listdir
from os.path import isfile, join

import yaml
try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader

from tests.utils import NOTION_ACCESS_TOKEN, parse_yaml_front_matter
from n2y.main import main
from n2y.notion import Client


def run_n2y(temp_dir, config):
    config_path = os.path.join(temp_dir, "config.yaml")
    with open(config_path, "w") as f:
        yaml.dump(config, f)
    old_cwd = os.getcwd()
    os.chdir(temp_dir)
    try:
        status = main([config_path], NOTION_ACCESS_TOKEN)
    finally:
        os.chdir(old_cwd)
    return status


def run_n2y_page(temp_dir, page_id, **export_config_keys):
    config = {
        "exports": [
            {
                "id": page_id,
                "node_type": "page",
                "output": "page.md",
                **export_config_keys,
            }
        ]
    }
    status = run_n2y(temp_dir, config)
    assert status == 0
    with open(str(temp_dir / "page.md"), "r") as f:
        page_as_markdown = f.read()
    return page_as_markdown


def run_n2y_custom(temp_dir, config):
    config_path = os.path.join(temp_dir, "config.yaml")
    with open(config_path, "w") as f:
        yaml.dump(config, f)
    old_cwd = os.getcwd()
    os.chdir(temp_dir)
    try:
        status = main([config_path], NOTION_ACCESS_TOKEN)
    finally:
        os.chdir(old_cwd)
    return status


def run_n2y_database_as_yaml(temp_dir, database_id, **export_config_keys):
    config = {
        "exports": [
            {
                "id": database_id,
                "node_type": "database_as_yaml",
                "output": "database.yml",
                **export_config_keys,
            }
        ]
    }
    status = run_n2y(temp_dir, config)
    assert status == 0
    with open(str(temp_dir / "database.yml"), "r") as f:
        unsorted_database = yaml.load(f, Loader=Loader)
    return unsorted_database


def run_n2y_database_as_files(temp_dir, database_id, **export_config_keys):
    config = {
        "exports": [
            {
                "id": database_id,
                "node_type": "database_as_files",
                "output": "database",
                **export_config_keys,
            }
        ]
    }
    status = run_n2y(temp_dir, config)
    assert status == 0
    return os.path.join(temp_dir, "database")


def test_simple_database_to_yaml(tmpdir):
    """
    The database can be seen here:
    https://fresh-pencil-9f3.notion.site/176fa24d4b7f4256877e60a1035b45a4
    """
    object_id = "176fa24d4b7f4256877e60a1035b45a4"
    unsorted_database = run_n2y_database_as_yaml(tmpdir, object_id, content_property="Content")
    database = sorted(unsorted_database, key=lambda row: row["Name"])
    assert len(database) == 3
    assert database[0]["Name"] == "A"
    assert database[0]["Tags"] == ["a", "b"]
    assert database[0]["Content"] == "A\n"


def test_big_database_to_yaml(tmpdir):
    """
    The database can be seen here:
    https://fresh-pencil-9f3.notion.site/9341a0ddf7d4442d94ad74e5100f72af
    """
    object_id = "9341a0ddf7d4442d94ad74e5100f72af"
    database = run_n2y_database_as_yaml(tmpdir, object_id)
    assert len(database) == 101


def test_simple_database_to_markdown_files(tmpdir):
    """
    The database can be seen here:
    https://fresh-pencil-9f3.notion.site/176fa24d4b7f4256877e60a1035b45a4
    """
    object_id = "176fa24d4b7f4256877e60a1035b45a4"
    output_directory = run_n2y_database_as_files(tmpdir, object_id, filename_template="{Name}.md")
    generated_files = {f for f in listdir(output_directory) if isfile(join(output_directory, f))}
    assert generated_files == {"A.md", "B.md", "C.md"}
    document = open(join(output_directory, "A.md"), "r").read()
    metadata = parse_yaml_front_matter(document)
    assert metadata["Name"] == "A"
    assert metadata["Tags"] == ["a", "b"]
    assert "content" not in metadata


def test_simple_database_to_docx_files(tmpdir):
    """
    The database can be seen here:
    https://fresh-pencil-9f3.notion.site/176fa24d4b7f4256877e60a1035b45a4
    """
    database_id = "176fa24d4b7f4256877e60a1035b45a4"
    config = {
        "exports": [
            {
                "id": database_id,
                "pandoc_format": "docx",
                "pandoc_options": ["--standalone"],
                "node_type": "database_as_files",
                "output": "database",
            }
        ]
    }
    status = run_n2y(tmpdir, config)
    assert status == 0
    output_directory = os.path.join(tmpdir, "database")
    generated_files = {f for f in listdir(output_directory) if isfile(join(output_directory, f))}
    assert generated_files == {"A.docx", "B.docx", "C.docx"}


def test_simple_database_config(tmpdir):
    """
    The database can be seen here:
    https://fresh-pencil-9f3.notion.site/176fa24d4b7f4256877e60a1035b45a4
    """
    database_id = "176fa24d4b7f4256877e60a1035b45a4"
    notion_sorts = [
        {
            "property": "Name",
            "direction": "descending",
        }
    ]
    notion_filter = {
        "or": [
            {"property": "Name", "rich_text": {"contains": "A"}},
            {"property": "Name", "rich_text": {"contains": "C"}},
        ]
    }
    database = run_n2y_database_as_yaml(
        tmpdir, database_id,
        notion_sort=notion_sorts, notion_filter=notion_filter,
    )
    assert len(database) == 2
    assert database[0]["Name"] == "C"
    assert database[1]["Name"] == "A"


def test_all_properties_database(tmpdir):
    """
    The page can be seen here:
    https://fresh-pencil-9f3.notion.site/53b9fa3da3f348e7ba3346254f1c722f
    """
    object_id = "53b9fa3da3f348e7ba3346254f1c722f"
    database = run_n2y_database_as_yaml(tmpdir, object_id)
    assert len(database) == 4


def test_mention_in_simple_table(tmpdir):
    '''
    The page can be seen here:
    https://fresh-pencil-9f3.notion.site/Simple-Table-with-Mention-Test-e12497428b0e43c3b14e016de6c5a2cf
    '''
    object_id = 'e12497428b0e43c3b14e016de6c5a2cf'
    document = run_n2y_page(tmpdir, object_id)
    assert "In Table: Simple Test Page" in document
    assert "Out of Table: Simple Test Page" in document


def test_all_blocks_page_to_markdown(tmpdir):
    """
    The page can be seen here:
    https://fresh-pencil-9f3.notion.site/Test-Page-5f18c7d7eda44986ae7d938a12817cc0
    """
    object_id = "5f18c7d7eda44986ae7d938a12817cc0"
    document = run_n2y_page(tmpdir, object_id)
    lines = document.split("\n")
    metadata = parse_yaml_front_matter(document)
    assert metadata["title"] == "All Blocks Test Page"
    column_strings_in_lines = [
        "Column 1" in lines,
        "Column 1.1" in lines,
        "Column 1.2" in lines,
        "Column 2" in lines,
    ]

    assert "Text block" in lines
    assert "Text *italics* too" in lines
    assert "-   [ ] To do list block" in lines
    assert "# Heading 1" in lines
    assert "## Heading 2" in lines
    assert "### Heading 3" in lines
    assert "-   List block" in lines
    assert "1.  Number list block" in lines
    assert "-   Toggle list" in lines
    assert "> Block quote single paragraph" in lines
    assert "> Block quote second paragraph" in lines
    assert "---" in lines
    assert "Callout block" in lines
    assert "$e^{-i \\pi} = -1$" in lines
    assert "``` javascript\nCode Block\n```" in document
    assert lines.count("This is a synced block.") == 2
    assert "This is a synced block from another page." in lines
    assert all(column_strings_in_lines)
    assert "Mention: Simple Test Page" in lines
    assert "Simple Test Page" in lines  # from the LinkToPageBlock
    assert "Mention: Simple Test Database" in lines
    assert "Simple Test Database" in lines  # from the LinkToPageBlock

    # a bookmark with a caption and without
    assert "<https://innolitics.com>" in lines
    assert "[Bookmark caption](https://innolitics.com)" in lines

    # TODO: Add assertions about audio blocks and video blocks

    # the word "caption" is bolded
    assert "![Image **caption**](media/All_Blocks_Test_Page-5f1b0813453.jpeg)" in lines

    # from a file block in the Notion page
    assert os.path.exists(tmpdir / "media" / "All_Blocks_Test_Page-5f1b0813453.jpeg")


def test_page_in_database_to_markdown(tmpdir):
    """
    This test exports a single page, or "row", that is in a database. Unlike
    pages that are not in a database, who only have a single "Title" property,
    pages in a database will have properties for all of the "columns" in that
    database.

    The page can be seen here:
    https://fresh-pencil-9f3.notion.site/C-7e967a44893f4b25917965896e81c137
    """
    object_id = "7e967a44893f4b25917965896e81c137"
    document = run_n2y_page(tmpdir, object_id)
    lines = document.split("\n")
    metadata = parse_yaml_front_matter(document)
    assert metadata["Name"] == "C"
    assert metadata["Tags"] == ["d", "a", "b", "c"]
    assert "content" not in metadata
    assert "Has some basic content" in lines


def test_simple_page_to_markdown(tmpdir):
    """
    The page can be seen here:
    https://fresh-pencil-9f3.notion.site/Simple-Test-Page-6670dc17a7bc4426b91bca4cf3ac5623
    """
    object_id = "6670dc17a7bc4426b91bca4cf3ac5623"
    document = run_n2y_page(tmpdir, object_id)
    assert "Page content" in document


def test_builtin_plugins(tmpdir):
    """
    The page can be seen here:
    https://fresh-pencil-9f3.notion.site/Plugins-Test-96d71e2876eb47b285833582e8cf27eb
    """
    object_id = "96d71e2876eb47b285833582e8cf27eb"
    document = run_n2y_page(tmpdir, object_id, plugins=[
        "n2y.plugins.deepheaders",
        "n2y.plugins.removecallouts",
        "n2y.plugins.rawcodeblocks",
        "n2y.plugins.mermaid",
        "n2y.plugins.footnotes",
        "n2y.plugins.expandlinktopages",
    ])
    lines = document.split("\n")

    assert "#### H4" in lines
    assert "##### H5" in lines
    # TODO: Fix failing mermaid assertions
    # assert not any("should disappear" in l for l in lines)
    # invalid_mermaid = '    invalid'
    # assert lines[15] != invalid_mermaid
    # if lines[15] == '    sequenceDiagram':
    #     assert lines[16] == '    A->>B: Hello'
    #     assert lines[18] == invalid_mermaid
    # else:
    #     assert lines[17] == invalid_mermaid
    #     assert 'media' in lines[15]
    #     im1_line = re.search(r'media.*png', lines[15])[0]
    #     im1 = f'{tmpdir.strpath}/{im1_line}'
    #     root = Path(__file__).resolve().parent.parent
    #     with open(im1, 'rb') as img:
    #         with open(root / 'n2y' / 'data' / 'mermaid_err.png', 'rb') as err:
    #             assert img.read() != err.read()

    assert "Raw markdown should show up" in lines
    assert "Raw html should not show up" not in lines

    # TODO: Fix these failing assertions
    # assert "# Header with Footnotes[^1]" in lines
    # assert "Paragraph with footnote.[^2]" in lines
    # assert "[^1]: First **footnote**." in lines
    # assert "[^2]: Second footnote" in lines

    # The word "Bulletlist" only shows up in the linked page that is expanded
    assert "Bulletlist" in document

    # Ensure a link to page to an unshared page doesn't get expanded; note that
    # Notion will actually represent these pages as an "UnsupportedBlock" (which
    # is odd). This will throw a warning and won't produce any content though,
    # which is the desired behavior.
    assert "Untitled" not in document
    assert "Unshared Page" not in document
    assert "This page is not shared with the integration." not in document


def test_comment():
    # TODO: Add a link to page where this block can be seen
    block_with_comments_id = "ac496c7db16743488495976f7433dbfb"
    comments = Client(NOTION_ACCESS_TOKEN).get_comments(block_with_comments_id)
    assert comments[0].rich_text.to_plain_text() == "Test Comment"
    assert comments[1].rich_text.to_plain_text() == "Test Comment 2"


def test_can_pull_all_relations(tmpdir):
    """
    This page can be seen here https://www.notion.so/Item-e611d7fdd4604d1192637a25bc9f5339

    The purpose of this test is to confirm that we're handling pagination
    unrolling for situations when a relation property has more than 30 items.
    """
    object_id = "e611d7fdd4604d1192637a25bc9f5339"
    page = run_n2y_page(tmpdir, object_id)
    page_properties = parse_yaml_front_matter(page)
    assert len(page_properties["Related Items"]) == 31


def test_jinja_render_plugin(tmpdir):
    """
    This test exercises our jinja render plugin. It involves a simple database
    with three entries and a jinja code block.

    See https://www.notion.so/Render-Test-4803ad13c6224deb93da94c41cc105d3 for
    the parent page with the database and child page to be rendered.
    """
    object_id = "869e37f1523c468399411a1b23b27634"
    document = run_n2y_page(tmpdir, object_id, plugins=[
        "n2y.plugins.jinjarenderpage",
    ])

    assert "## blue is a color" in document
    assert "## pink is a color" in document
    assert "## red is a color" in document
    assert "Page with JinjaCodeBlock" in document


def test_dbfootnote_plugin(tmpdir):
    """
    This test exercises our database footnote. It involves a simple page with
    an inline database containing content for 3 footnotes.

    The page can be seen here:
    https://www.notion.so/Advanced-DB-Footnote-8a1a17c7ef3043f4bd9fb041ef31ba7
    """
    object_id = "8a1a17c7ef3043f4bd9fb041ef31ba7d"
    document = run_n2y_page(tmpdir, object_id, plugins=[
        "n2y.plugins.dbfootnotes",
    ])

    assert "some text [^1]." in document
    assert "like so [^2] and" in document
    assert "so [^3]." in document
    assert "[^1]: Inline DB content for footnote 1." in document
    assert "[^2]: Inline DB content for footnote 2." in document
    assert "[^3]: Inline DB content for footnote 3." in document


def test_simple_table_headers(caplog, tmp_path):
    """
    Simply show what flattened Markdown content is expected if the input
    contains tables without headers.

    Relies on https://www.notion.so/Simple-Tables-9b1dd705f61647b6a10032ec7671402f?pvs=4
    """
    object_id = "9b1dd705f61647b6a10032ec7671402f"

    content = run_n2y_page(tmp_path, object_id, pandoc_format="gfm")
    captured_messages = [
        r.message for r in caplog.records if r.levelno >= logging.WARNING
    ]

    number_expected_table_warnings = 0
    if (
        """\
Some text

|      |         |
|------|---------|
| This | has     |
| no   | headers |
"""
        in content
    ):
        number_expected_table_warnings += 1
    assert (
        """\
More text

|        | header | row     |
|--------|--------|---------|
| header | This   | has     |
| column | both   | headers |
|        |        |         |
| and    | an     | empty   |
"""
        in content
    )
    if (
        """\
Yakkity yakkity yakkity yak

|        |        |
|--------|--------|
| header | Fiddle |
| column | Faddle |
"""
        in content
    ):
        number_expected_table_warnings += 1
    assert """\
| header | row    |
|--------|--------|
| Nutter | Butter |
"""
    if number_expected_table_warnings > 0:
        expected_blurb = (
            f"{number_expected_table_warnings} table(s) will present empty "
            "headers to maintain Markdown spec"
        )
        assert any(expected_blurb in m for m in captured_messages)

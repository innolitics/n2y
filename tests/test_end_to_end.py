"""
These tests are run against a throw-away Notion account with a few pre-written
pages. Since this is a throw-away account, we're fine including the auth_token
in the codebase. The login for this throw-away account is in the Innolitics'
1password "Everyone" vault. If new test pages are added, this will need to be
used to create them.
"""
import sys
from os import listdir
import os.path
from os.path import isfile, join
from io import StringIO

import yaml
try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader

from tests.utils import NOTION_ACCESS_TOKEN, parse_yaml_front_matter
from n2y.main import main


def run_n2y(arguments):
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    sys.stdout = StringIO()
    sys.stderr = StringIO()
    try:
        status = main(arguments, NOTION_ACCESS_TOKEN)
        stdout = sys.stdout.getvalue()
        stderr = sys.stderr.getvalue()
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr
    return status, stdout, stderr


def test_simple_database_to_yaml():
    '''
    The database can be seen here:
    https://fresh-pencil-9f3.notion.site/176fa24d4b7f4256877e60a1035b45a4
    '''
    object_id = '176fa24d4b7f4256877e60a1035b45a4'
    status, stdoutput, _ = run_n2y([object_id, '--output', 'yaml'])
    assert status == 0
    unsorted_database = yaml.load(stdoutput, Loader=Loader)
    database = sorted(unsorted_database, key=lambda row: row["Name"])
    assert len(database) == 3
    assert database[0]["Name"] == "A"
    assert database[0]["Tags"] == ["a", "b"]
    assert database[0]["content"] is None


def test_simple_database_to_markdown_files(tmpdir):
    '''
    The database can be seen here:
    https://fresh-pencil-9f3.notion.site/176fa24d4b7f4256877e60a1035b45a4
    '''
    object_id = '176fa24d4b7f4256877e60a1035b45a4'
    status, _, _ = run_n2y([
        object_id,
        '--format', 'markdown',
        '--output', str(tmpdir),
    ])
    assert status == 0
    generated_files = {f for f in listdir(tmpdir) if isfile(join(tmpdir, f))}
    assert generated_files == {"A.md", "B.md", "C.md"}
    document_as_markdown = open(join(tmpdir, "A.md"), "r").read()
    metadata = parse_yaml_front_matter(document_as_markdown)
    assert metadata["Name"] == "A"
    assert metadata["Tags"] == ["a", "b"]
    assert "content" not in metadata


def test_simple_related_databases(tmpdir):
    """
    The page can be seen here:
    https://fresh-pencil-9f3.notion.site/Simple-Related-Databases-7737303365434ee6b699786c110830a2
    """
    object_id = "6cc54e2b49994787927c24a9ac3d4676"
    status, _, _ = run_n2y([
        object_id,
        '--format', 'yaml-related',
        '--output', str(tmpdir),
    ])
    assert status == 0
    generated_files = {f for f in listdir(tmpdir) if isfile(join(tmpdir, f))}
    assert generated_files == {"A.yml", "B.yml"}


def test_unshared_related_databases(tmpdir):
    """
    The page can be seen here:
    https://fresh-pencil-9f3.notion.site/bc86b1692c2e4b7d991d7e6f6cacac54?v=cb6887a78ddd41f1a8a75385f7a40d47
    """
    object_id = "bc86b1692c2e4b7d991d7e6f6cacac54"
    status, _, stderr = run_n2y([
        object_id,
        '--format', 'yaml-related',
        '--output', str(tmpdir),
    ])
    assert status == 0
    generated_files = {f for f in listdir(tmpdir) if isfile(join(tmpdir, f))}
    assert generated_files == {"Database_with_Relationship_to_Unshared_Database.yml"}
    # TODO: add an assertion that checks that warnings were displayed in stderr
    # (at the moment, they don't appear to be because the related pages simply
    # don't show up at all)


def test_all_properties_database():
    """
    The page can be seen here:
    https://fresh-pencil-9f3.notion.site/53b9fa3da3f348e7ba3346254f1c722f
    """
    object_id = '53b9fa3da3f348e7ba3346254f1c722f'
    status, stdoutput, _ = run_n2y([object_id, '--output', 'yaml'])
    assert status == 0
    unsorted_database = yaml.load(stdoutput, Loader=Loader)
    assert len(unsorted_database) == 4


def test_all_blocks_page_to_markdown(tmp_path):
    '''
    The page can be seen here:
    https://fresh-pencil-9f3.notion.site/Test-Page-5f18c7d7eda44986ae7d938a12817cc0
    '''
    object_id = '5f18c7d7eda44986ae7d938a12817cc0'
    status, document_as_markdown, stderr = run_n2y([object_id, '--media-root', str(tmp_path)])
    lines = document_as_markdown.split('\n')
    metadata = parse_yaml_front_matter(document_as_markdown)
    assert metadata['title'] == 'All Blocks Test Page'

    # TODO: look into why there's extra space in between the list entries
    assert status == 0
    assert "Text block" in lines
    assert "-   [ ] To do list block" in lines
    assert "# Heading 1" in lines
    assert "## Heading 2" in lines
    assert "### Heading 3" in lines
    assert "-   List block" in lines
    assert "1.  Number list block" in lines
    assert "-   Toggle list" in lines
    assert "> Block quote" in lines
    assert "---" in lines
    assert "Callout block" in lines
    assert "$e^{-i \\pi} = -1$" in lines
    assert "``` javascript\nCode Block\n```" in document_as_markdown

    # a bookmark with a caption and without
    assert "<https://innolitics.com>" in lines
    assert "[Bookmark caption](https://innolitics.com)" in lines

    # the word "caption" is bolded
    assert "![Image **caption**](All_Blocks_Test_Page-4e1e6c89.jpeg)" in lines

    # "Unknown.jpeg" is a file block in the Notion page
    assert os.path.exists(tmp_path / "All_Blocks_Test_Page-4e1e6c89.jpeg")


def test_page_in_database_to_markdown():
    '''
    This test exports a single page, or "row", that is in a database. Unlike
    pages that are not in a database, who only have a single "Title" property,
    pages in a database will have properties for all of the "columns" in that
    database.

    The page can be seen here:
    https://fresh-pencil-9f3.notion.site/C-7e967a44893f4b25917965896e81c137
    '''
    object_id = '7e967a44893f4b25917965896e81c137'
    _, document_as_markdown, _ = run_n2y([object_id])
    lines = document_as_markdown.split('\n')
    metadata = parse_yaml_front_matter(document_as_markdown)
    assert metadata['Name'] == 'C'
    assert metadata['Tags'] == ['d', 'a', 'b', 'c']
    assert "content" not in metadata
    assert 'Has some basic content' in lines


def test_simple_page_to_markdown():
    '''
    The page can be seen here:
    https://fresh-pencil-9f3.notion.site/Simple-Test-Page-6670dc17a7bc4426b91bca4cf3ac5623
    '''
    object_id = '6670dc17a7bc4426b91bca4cf3ac5623'
    status, document_as_markdown, _ = run_n2y([object_id])
    assert status == 0
    assert "Page content" in document_as_markdown


def test_builtin_plugins():
    '''
    The page can be seen here:
    https://fresh-pencil-9f3.notion.site/Plugins-Test-96d71e2876eb47b285833582e8cf27eb
    '''
    object_id = "96d71e2876eb47b285833582e8cf27eb"
    status, document_as_markdown, _ = run_n2y([
        object_id,
        '--plugin', 'n2y.plugins.deepheaders',
        '--plugin', 'n2y.plugins.removecallouts',
        '--plugin', 'n2y.plugins.rawcodeblocks',
    ])
    assert status == 0
    lines = document_as_markdown.split('\n')
    assert '#### H4' in lines
    assert '##### H5' in lines
    assert not any('should disappear' in l for l in lines)
    assert not any('```' in l for l in lines)
    assert 'Raw markdown should show up' in lines
    assert 'Raw html should not show up' not in lines


def test_missing_object_exception():
    invalid_page_id = "11111111111111111111111111111111"
    assert run_n2y([invalid_page_id]) != 0

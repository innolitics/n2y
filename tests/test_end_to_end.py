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

import pytest
import yaml
try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader

from tests.utils import NOTION_ACCESS_TOKEN, parse_yaml_front_matter
from n2y.main import main
from n2y.errors import APIErrorCode, HTTPResponseError


def run_n2y(arguments):
    old_stdout = sys.stdout
    sys.stdout = StringIO()
    status = main(arguments, NOTION_ACCESS_TOKEN)
    captured_stdout = sys.stdout.getvalue()
    sys.stdout = old_stdout
    return status, captured_stdout


def test_simple_database_to_yaml():
    '''
    The database can be seen here:
    https://fresh-pencil-9f3.notion.site/176fa24d4b7f4256877e60a1035b45a4
    '''
    object_id = '176fa24d4b7f4256877e60a1035b45a4'
    status, stdoutput = run_n2y([object_id, '--output', 'yaml'])
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
    status, _ = run_n2y([
        object_id,
        '--format', 'markdown',
        '--output', str(tmpdir),
        '--name-column', 'Name',
    ])
    assert status == 0
    generated_files = {f for f in listdir(tmpdir) if isfile(join(tmpdir, f))}
    assert generated_files == {"A.md", "B.md", "C.md"}
    document_as_markdown = open(join(tmpdir, "A.md"), "r").read()
    metadata = parse_yaml_front_matter(document_as_markdown)
    assert metadata["Name"] == "A"
    assert metadata["Tags"] == ["a", "b"]
    assert "content" not in metadata


@pytest.mark.xfail(reason="The Notion API doesn't seem to include relation property objects")
def test_related_databases(tmpdir):
    """
    The page can be seen here:
    https://fresh-pencil-9f3.notion.site/Related-Databases-Page-26b1b681c3f6423c85989c40cc461e82
    """
    object_id = "53b9fa3da3f348e7ba3346254f1c722f"
    status, _ = run_n2y([
        object_id,
        '--format', 'yaml-related',
        '--output', str(tmpdir),
    ])
    assert status == 0
    generated_files = {f for f in listdir(tmpdir) if isfile(join(tmpdir, f))}
    assert generated_files == {"People.yml", "Employer.yml", "Countries.yml"}


def test_all_properties_database():
    """
    The page can be seen here:
    https://fresh-pencil-9f3.notion.site/53b9fa3da3f348e7ba3346254f1c722f
    """
    object_id = '53b9fa3da3f348e7ba3346254f1c722f'
    status, stdoutput = run_n2y([object_id, '--output', 'yaml'])
    assert status == 0
    unsorted_database = yaml.load(stdoutput, Loader=Loader)
    assert len(unsorted_database) == 4


def test_all_blocks_page_to_markdown(tmp_path):
    '''
    The page can be seen here:
    https://fresh-pencil-9f3.notion.site/Test-Page-5f18c7d7eda44986ae7d938a12817cc0
    '''
    object_id = '5f18c7d7eda44986ae7d938a12817cc0'
    status, document_as_markdown = run_n2y([object_id, '--media-root', str(tmp_path)])
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
    assert "![Image **caption**](Unknown.jpeg)" in lines
    # TODO: add more blocks to the document, along with assertions

    # "Unknown.jpeg" is a file block in the Notion page
    assert os.path.exists(tmp_path / "Unknown.jpeg")


def test_page_in_database_to_markdown():
    '''
    This test exports a single page, or "row", that is in a database. Unlike
    pages that are not in a databe, who only have a single "Title" property,
    pages in a database will have properties for all of the "columns" in that
    database.

    The page can be seen here:
    https://fresh-pencil-9f3.notion.site/C-7e967a44893f4b25917965896e81c137
    '''
    object_id = '7e967a44893f4b25917965896e81c137'
    _, document_as_markdown = run_n2y([object_id])
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
    status, document_as_markdown = run_n2y([object_id])
    assert status == 0
    assert "Page content" in document_as_markdown


def test_missing_object_exception():
    invalid_page_id = "11111111111111111111111111111111"
    with pytest.raises(HTTPResponseError) as exinfo:
        run_n2y([invalid_page_id])
    assert exinfo.value.code == APIErrorCode.ObjectNotFound

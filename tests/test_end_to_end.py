"""
These tests are run against a throw-away Notion account with a few pre-written
pages. Since this is a throw-away account, we're fine including the auth_token
in the codebase. The login for this throw-away account is in the Innolitics'
1password "Everyone" vault. If new test pages are added, this will need to be
used to create them.
"""
import sys
from io import StringIO

import pytest
import yaml
try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader

from tests.utils import NOTION_ACCESS_TOKEN
from n2y.main import main


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
    database = sorted(unsorted_database, key=lambda row: row["name"])
    assert len(database) == 3
    assert database[0]["name"] == "A"
    assert database[0]["tags"] == ["a", "b"]
    assert database[0]["content"] is None


@pytest.mark.xfail(reason="page export not yet supported")
def test_simple_page_to_markdown():
    '''
    The page can be seen here:
    https://fresh-pencil-9f3.notion.site/Test-Page-5f18c7d7eda44986ae7d938a12817cc0
    '''
    object_id = '5f18c7d7eda44986ae7d938a12817cc0'
    document_as_markdown = run_n2y([object_id])
    assert "Text block" in document_as_markdown
    assert "- [ ] To do list block" in document_as_markdown
    assert "# Heading 1" in document_as_markdown
    assert "## Heading 2" in document_as_markdown
    assert "### Heading 3" in document_as_markdown
    assert "- List block" in document_as_markdown
    assert "1. Number list block" in document_as_markdown
    # TODO: add more blocks to the document, along with assertions

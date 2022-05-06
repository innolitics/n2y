"""
These tests are run against a throw-away Notion account with a few pre-written
pages. Since this is a throw-away account, we're fine including the auth_token
in the codebase. The login for this throw-away account is in the Innolitics'
1password "Everyone" vault. If new test pages are added, this will need to be
used to create them.
"""
import shutil
import os
import subprocess

import yaml
try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader


def run_n2y(arguments, env=None):
    if env is None:
        env = {}
    pandoc_path = shutil.which('pandoc')
    assert pandoc_path is not None
    default_env = {
        # This is not a security risk because the integration token that
        # provides read-only access to public notion pages in a throw-away
        # notion account.
        "NOTION_ACCESS_TOKEN": 'secret_lylx4iL5awveY3re6opuvSQqM6sMRu572TowhfzPy5r',
        "PATH": os.path.dirname(pandoc_path),  # ensures pandoc can be found
    }
    n2y_path = shutil.which('n2y')
    assert n2y_path is not None
    return subprocess.check_output([n2y_path, *arguments], env={**default_env, **env})


def test_simple_database_to_yaml():
    '''
    The database can be seen here:
    https://fresh-pencil-9f3.notion.site/176fa24d4b7f4256877e60a1035b45a4
    '''
    object_id = '176fa24d4b7f4256877e60a1035b45a4'
    output = run_n2y([object_id, '--output', 'yaml'])
    unsorted_database = yaml.load(output, Loader=Loader)
    database = sorted(unsorted_database, key=lambda row: row["name"])
    assert len(database) == 3
    assert database[0]["name"] == "A"
    assert database[0]["tags"] == ["a", "b"]
    assert database[0]["content"] is None


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

"""
These tests are run against a throw-away Notion account with a few pre-written
pages. Since this is a throw-away account, we're fine including the auth_token
in the codebase.
"""
import shutil
import os
import subprocess

import yaml
try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader

AUTH_TOKEN = 'secret_lylx4iL5awveY3re6opuvSQqM6sMRu572TowhfzPy5r'


def test_simple_database_to_yaml():
    database = '176fa24d4b7f4256877e60a1035b45a4'
    pandoc_path = shutil.which('pandoc')
    assert pandoc_path is not None
    env = {
        "NOTION_ACCESS_TOKEN": AUTH_TOKEN,
        "PATH": os.path.dirname(pandoc_path),  # ensures pandoc can be found
    }
    n2y_path = shutil.which('n2y')
    output = subprocess.check_output([n2y_path, database, '--output', 'yaml'], env=env)
    unsorted_database = yaml.load(output, Loader=Loader)
    database = sorted(unsorted_database, key=lambda row: row["name"])
    assert len(database) == 3
    assert database[0]["name"] == "A"
    assert database[0]["tags"] == ["a", "b"]
    assert database[0]["content"] is None

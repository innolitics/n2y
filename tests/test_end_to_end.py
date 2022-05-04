"""
These tests are run against a throw-away Notion account with a few pre-written
pages. Since this is a throw-away account, we're fine including the auth_token
in the codebase.
"""
import subprocess

import yaml

AUTH_TOKEN = 'secret_lylx4iL5awveY3re6opuvSQqM6sMRu572TowhfzPy5r'


def test_database_to_yaml(tmpdir):
    database_url = 'https://www.notion.so/176fa24d4b7f4256877e60a1035b45a4?v=130ffd3224fd4512871bb45dbceaa7b2'
    output = subprocess.check_output(['n2y', database_url, '--output', 'yaml'])
    database = yaml.load(output)
    assert len(database) == 3
    assert database[0]["Name"] == "A"
    assert database[0]["Tags"] == ["a", "b"]

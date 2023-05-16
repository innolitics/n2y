import pytest  # noqa: E401

import os

@pytest.fixture(scope="session")
def access_token():
    return os.getenv("NOTION_ACCESS_TOKEN") or \
        'secret_lylx4iL5awveY3re6opuvSQqM6sMRu572TowhfzPy5r'

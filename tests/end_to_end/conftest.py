import pytest

import os

NOTION_ACCESS_TOKEN = os.getenv("NOTION_ACCESS_TOKEN") or \
                      "secret_lylx4iL5awveY3re6opuvSQqM6sMRu572TowhfzPy5r"


@pytest.fixture()
def valid_access_token(monkeypatch):
    with monkeypatch.context() as m:
        m.setenv("NOTION_ACCESS_TOKEN", NOTION_ACCESS_TOKEN)
        yield NOTION_ACCESS_TOKEN

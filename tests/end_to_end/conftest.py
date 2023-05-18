import pytest  # noqa: F401

from tests.utils import NOTION_ACCESS_TOKEN


@pytest.fixture()
def valid_access_token(monkeypatch):
    with monkeypatch.context() as m:
        m.setenv("NOTION_ACCESS_TOKEN", NOTION_ACCESS_TOKEN)
        yield NOTION_ACCESS_TOKEN

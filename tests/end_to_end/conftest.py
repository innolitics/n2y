import pytest  # noqa: F401

# Some end-to-end tests are run against a throw-away Notion account with a few
# pre-written pages. Since this is a throw-away account, we're fine including
# the auth_token in the codebase. The login for this throw-away account is in
# the Innolitics' 1password "Everyone" vault. If new test pages are added, this
# will need to be used to create them.
NOTION_ACCESS_TOKEN = "secret_lylx4iL5awveY3re6opuvSQqM6sMRu572TowhfzPy5r"


@pytest.fixture()
def valid_access_token(monkeypatch):
    with monkeypatch.context() as m:
        m.setenv("NOTION_ACCESS_TOKEN", NOTION_ACCESS_TOKEN)
        yield NOTION_ACCESS_TOKEN

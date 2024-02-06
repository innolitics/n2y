import hashlib
from unittest.mock import MagicMock, patch

from n2y.notion import Client
from n2y.notion_mocks import mock_page, mock_property_value, mock_user
from n2y.page import Page
from n2y.plugins.downloadfileproperty import DownloadFilePropertyValue
from n2y.user import User
from n2y.utils import slugify


@patch("n2y.notion.Client.wrap_notion_user")
def mock_page_with_file_property(tmp_dir: str, mk_wrap_notion_user: MagicMock) -> Page:
    client = Client(
        "",
        plugins=["n2y.plugins.downloadfileproperty"],
        media_root=tmp_dir,
        media_url="http://foo.com/",
    )
    mk_wrap_notion_user.return_value = User(client, mock_user())
    file_prop = mock_property_value(
        "files",
        [
            {
                "name": "Notion Developer Image",
                "type": "external",
                "external": {
                    "url": "https://files.readme.io/a267aac-notion-devs-logo.svg"
                },
            }
        ],
    )
    notion_page = mock_page(extra_properties={"Files": file_prop})
    page = Page(client, notion_page)
    page._children = []
    return page


def test_downloadfileproperty_class_is_used(tmpdir):
    page = mock_page_with_file_property(tmpdir)
    file_prop = page.properties["Files"]
    assert isinstance(file_prop, DownloadFilePropertyValue)


def test_file_is_downloaded(tmpdir):
    page = mock_page_with_file_property(tmpdir)
    file_prop: DownloadFilePropertyValue = page.properties["Files"]
    urls: list[str] = file_prop.to_value(None, None)
    assert len(urls) == 1
    assert urls[0].startswith("http://foo.com/")
    assert urls[0].endswith(".svg")
    assert len(tmpdir.listdir()) == 1
    assert tmpdir.listdir()[0].ext == ".svg"
    assert tmpdir.listdir()[0].size() > 0


def test_filename_format(tmpdir):
    page = mock_page_with_file_property(tmpdir)
    file_prop: DownloadFilePropertyValue = page.properties["Files"]
    urls: list[str] = file_prop.to_value(None, None)
    assert len(urls) == 1
    url_path = urls[0]
    file_path = str(tmpdir.listdir()[0])
    page_title_slug = slugify(page.title.to_plain_text())
    with open(file_path, "rb") as f:
        file_content = f.read()
    file_hash = file_hash = hashlib.sha256(file_content).hexdigest()[:10]
    assert url_path.endswith(f"{page_title_slug}-{file_hash}.svg")
    assert file_path.endswith(f"{page_title_slug}-{file_hash}.svg")


def test_file_naming_is_consistent(tmpdir):
    page = mock_page_with_file_property(tmpdir)
    file_prop: DownloadFilePropertyValue = page.properties["Files"]
    urls: list[str] = file_prop.to_value(None, None)
    urls_2: list[str] = file_prop.to_value(None, None)
    assert urls == urls_2
    assert len(tmpdir.listdir()) == 1

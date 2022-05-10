import pytest

from n2y.errors import APIErrorCode, HTTPResponseError
from n2y.notion import Client
from tests.utils import NOTION_ACCESS_TOKEN


def test_missing_object_exception():
    client = Client(NOTION_ACCESS_TOKEN)
    invalid_page_id = "11111111111111111111111111111111"
    with pytest.raises(HTTPResponseError) as exinfo:
        client.get_page(invalid_page_id)
    assert exinfo.value.code == APIErrorCode.ObjectNotFound

from datetime import datetime, timedelta, timezone
from math import isclose

import pytest
from pandoc.types import MetaBool, MetaList, MetaMap, MetaString
from pytest import raises

from n2y.errors import APIErrorCode, APIResponseError, ConnectionThrottled
from n2y.notion import Client
from n2y.utils import (
    fromisoformat,
    header_id_from_text,
    id_from_share_link,
    retry_api_call,
    yaml_to_meta_value,
)

foo_token = "foo_token"
rate_limited_status_code = 429


def test_fromisoformat_datetime():
    expected = datetime(2022, 5, 10, 19, 52, tzinfo=timezone.utc)
    assert fromisoformat("2022-05-10T19:52:00.000Z") == expected


def test_fromisoformat_date():
    expected = datetime(2022, 5, 11)
    assert fromisoformat("2022-05-11") == expected


def test_database_id_from_share_link_id():
    database_id = "f77db3af4ab6a47b6162dacd76681231"
    assert id_from_share_link(database_id) == database_id


def test_database_id_from_share_link_id_hyphens():
    database_id = "f77db3af4ab6a47b6162dacd76681231"
    database_id_hyphens = "f77db3af-4ab6a47b6162dacd-76681231"
    assert id_from_share_link(database_id_hyphens) == database_id


def test_database_id_from_share_link_no_hyphens():
    database_id = "f77db3af4ab6a47b6162dacd76681231"
    view_id = "463a296148dc38f791e7037dda9a8c3f"
    share_link = f"https://www.notion.so/ws/{database_id}?v={view_id}"
    assert id_from_share_link(share_link) == database_id


def test_database_id_from_share_link_hyphens():
    database_id = "90a3f77db3af4ab6a47b6162dacd1111"
    database_id_hyphens = "90a3f77-db3af4ab6a47b6162-dacd1111"
    view_id = "463a296148dc38f791e7037dda9a8c3f"
    share_link = f"https://www.notion.so/ws/{database_id_hyphens}?v={view_id}"
    assert id_from_share_link(share_link) == database_id


def test_page_id_from_share_link():
    page_id = "42361d2334624e949d9b7e94d30c988b"
    share_link = f"https://www.notion.so/innolitics/SaMD-DHF-Template-{page_id}"
    assert id_from_share_link(share_link) == page_id


class MockResponse:
    def __init__(self, time, status_code):
        self.headers = {"retry-after": time}
        self.text = ""
        self.status_code = status_code


def test_retry_api_call_no_error():
    client = Client(foo_token)

    @retry_api_call
    def tester(_):
        return True

    assert tester(client)


def test_retry_api_call_multiple_errors():
    client = Client(foo_token)
    call_count = 0

    @retry_api_call
    def tester(_, time):
        seconds = timedelta.total_seconds(datetime.now() - time)
        nonlocal call_count
        call_count += 1

        if call_count == 1:
            raise ConnectionThrottled(MockResponse(0.05, rate_limited_status_code))
        elif call_count == 2:
            assert isclose(0.05, seconds, abs_tol=0.1)
            raise ConnectionThrottled(MockResponse(0.23, rate_limited_status_code))
        elif call_count == 3:
            assert isclose(0.35, seconds, abs_tol=0.1)
            raise ConnectionThrottled(MockResponse(0.16, rate_limited_status_code))
        elif call_count == 4:
            assert isclose(0.51, seconds, abs_tol=0.1)
            return True

    assert tester(client, datetime.now())


@pytest.mark.parametrize("code", APIErrorCode.RetryableCodes)
def test_retry_api_call_once(code):
    call_count = 0
    client = Client(foo_token)

    @retry_api_call
    def tester(_):
        nonlocal call_count
        call_count += 1

        if call_count == 1:
            if code == APIErrorCode.RateLimited:
                raise ConnectionThrottled(MockResponse(0.001, rate_limited_status_code))
            raise APIResponseError(MockResponse(0.001, 500), "", code)
        else:
            return True

    assert tester(client)
    assert call_count == 2


def test_retry_api_call_max_errors():
    client = Client(foo_token)

    @retry_api_call
    def tester(_):
        raise ConnectionThrottled(MockResponse(0.001, rate_limited_status_code))

    with raises(ConnectionThrottled):
        tester(client)


def test_retry_api_call_retry_false():
    client = Client(foo_token, retry=False)

    @retry_api_call
    def tester(_):
        raise ConnectionThrottled(MockResponse(0.001, rate_limited_status_code))

    with raises(ConnectionThrottled):
        tester(client)


def test_yaml_to_meta_value_scalar():
    assert yaml_to_meta_value("test") == MetaString("test")
    assert yaml_to_meta_value(3) == MetaString("3")
    assert yaml_to_meta_value(3.45) == MetaString("3.45")
    assert yaml_to_meta_value(True) == MetaBool(True)
    assert yaml_to_meta_value(False) == MetaBool(False)
    assert yaml_to_meta_value(None) == MetaString("")


def test_yaml_to_meta_value_map():
    assert yaml_to_meta_value({"a": "1", "b": 2}) == MetaMap(
        {
            "a": MetaString("1"),
            "b": MetaString("2"),
        }
    )


def test_yaml_to_meta_value_list():
    assert yaml_to_meta_value(["a", 1]) == MetaList([MetaString("a"), MetaString("1")])


def test_header_id_from_text_basic():
    assert header_id_from_text("Essays") == "essays"
    assert header_id_from_text("Hello Goodbye") == "hello-goodbye"


def test_header_id_from_text():
    """
    Most of these test cases were taken from the pandoc documentation. See:
    https://pandoc.org/MANUAL.html#extension-auto_identifiers
    """
    assert (
        header_id_from_text("Heading identifiers in HTML")
        == "heading-identifiers-in-html"
    )
    assert header_id_from_text("Maître d'hôtel") == "maître-dhôtel"
    assert header_id_from_text("*Dogs*?--in *my* house?") == "dogs--in-my-house"
    assert header_id_from_text("[HTML], [S5], or [RTF]?") == "html-s5-or-rtf"
    assert header_id_from_text("3. Applications") == "applications"
    assert header_id_from_text("33") == "section"

    # These are additional tests constructed by us.
    assert header_id_from_text("33 section") == "section"
    assert header_id_from_text("") == "section"
    assert header_id_from_text("newlines\nare hyphens") == "newlines-are-hyphens"


def test_header_id_from_text_existing_ids():
    assert header_id_from_text("a", {"a"}) == "a-1"
    assert header_id_from_text("a", {"a", "a-1"}) == "a-2"
    assert header_id_from_text("", {"section", "section-1"}) == "section-2"
    assert header_id_from_text("", {"section", "a", "a-1"}) == "section-1"

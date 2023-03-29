from math import isclose
from pytest import raises
from datetime import datetime, timezone, timedelta

from n2y.errors import APIResponseError
from n2y.notion_mocks import MockResponse
from n2y.notion import retry_api_call, Client
from n2y.utils import fromisoformat, id_from_share_link, DEFAULT_MAX_RETRIES


def test_fromisoformat_datetime():
    expected = datetime(2022, 5, 10, 19, 52, tzinfo=timezone.utc)
    assert fromisoformat('2022-05-10T19:52:00.000Z') == expected


def test_fromisoformat_date():
    expected = datetime(2022, 5, 11)
    assert fromisoformat('2022-05-11') == expected


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
    page_id = '42361d2334624e949d9b7e94d30c988b'
    share_link = f'https://www.notion.so/innolitics/SaMD-DHF-Template-{page_id}'
    assert id_from_share_link(share_link) == page_id


def test_retry_api_call_no_error():
    @retry_api_call
    def tester(client):
        return True

    assert tester(Client(''))


def test_retry_api_call_errors():
    status_code = 429

    @retry_api_call
    def tester(_, time):
        seconds = timedelta.total_seconds(datetime.now() - time)
        if retry_api_call.retry_count == 0:
            raise APIResponseError(MockResponse(0.12, status_code), '', status_code)
        elif retry_api_call.retry_count == 1:
            assert isclose(0.12, seconds, abs_tol=0.1)
            raise APIResponseError(MockResponse(0.23, status_code), '', status_code)
        elif retry_api_call.retry_count == 2:
            assert isclose(0.35, seconds, abs_tol=0.1)
            raise APIResponseError(MockResponse(0.16, status_code), '', status_code)
        elif retry_api_call.retry_count == 3:
            assert isclose(0.51, seconds, abs_tol=0.1)
            return True

    client = Client('')
    assert tester(client, datetime.now())


def test_retry_api_call_max_errors():
    status_code = 429

    @retry_api_call
    def tester(_, time):
        seconds = timedelta.total_seconds(datetime.now() - time)
        if retry_api_call.retry_count == 0:
            raise APIResponseError(MockResponse(0.12, status_code), '', status_code)
        elif retry_api_call.retry_count == 1:
            assert isclose(0.12, seconds, abs_tol=0.1)
            raise APIResponseError(MockResponse(0.23, status_code), '', status_code)
        elif retry_api_call.retry_count == 2:
            assert isclose(0.35, seconds, abs_tol=0.1)
            raise APIResponseError(MockResponse(0.16, status_code), '', status_code)
        elif retry_api_call.retry_count == 3:
            assert isclose(0.51, seconds, abs_tol=0.1)
            raise APIResponseError(MockResponse(0.2, status_code), '', status_code)

    client = Client('')
    with raises(APIResponseError):
        tester(client, datetime.now())


def test_retry_api_call_multiple_calls():
    status_code = 429

    @retry_api_call
    def test_1(_):
        if retry_api_call.retry_count == 0:
            raise APIResponseError(MockResponse(0.12, status_code), '', status_code)
        elif retry_api_call.retry_count == 1:
            return True

    @retry_api_call
    def test_2(_):
        if retry_api_call.retry_count == 0:
            return True
        return False
    client = Client('')
    assert test_1(client)
    assert test_2(client)

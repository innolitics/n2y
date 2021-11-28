import pytest

from notion import id_from_share_link


def test_database_id_from_share_link_no_hyphens():
    database_id = "90a3f77db3af4ab6a47b6162dacd76681231"
    view_id = "463a296148dc38f791e7037dda9a8c3f"
    share_link = f"https://www.notion.so/ws/{database_id}?v={view_id}"
    assert id_from_share_link(share_link) == database_id


def test_database_id_from_share_link_hyphens():
    database_id = "90a3f77db3af4ab6a47b6162dacd76681231"
    database_id_hyphens = "90a3f77-db3af4ab6a47b6162-dacd76681231"
    view_id = "463a296148dc38f791e7037dda9a8c3f"
    share_link = f"https://www.notion.so/ws/{database_id_hyphens}?v={view_id}"
    assert id_from_share_link(share_link) == database_id


def test_database_id_from_share_link_not_36_long():
    database_id = "90a3f77db3af4ab6a47b6162da7668"
    view_id = "463a296148dc38f791e7037dda9a8c3f"
    share_link = f"https://www.notion.so/ws/{database_id}?v={view_id}"
    with pytest.raises(ValueError):
        id_from_share_link(share_link)

BASE_NOTION_API_URL = "https://api.notion.com/v1/"


class Client:
    def __init__(self, access_token):
        self.access_token = access_token


def id_from_share_link(share_link):
    # see tests
    database_id = share_link.split("/")[-1].split("?")[0].replace("-", "")
    if len(database_id) != 36:
        raise ValueError(f"Notion database ID {database_id} is not 36 characters long as expected")
    return database_id

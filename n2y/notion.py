import json

import requests


class Client:
    def __init__(self, access_token):
        self.access_token = access_token
        self.base_url = "https://api.notion.com/v1/"

    def get_database(self, database_id):
        starting_url = f"{self.base_url}databases/{database_id}/query"

        def depaginator(url):
            while True:
                data = self._get_database(url, database_id)
                yield data["results"]
                if not data["has_more"]:
                    return
                else:
                    url = data["next_cursor"]

        return sum(depaginator(starting_url), [])


    def _get_database(self, url, database_id):
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "Notion-Version": "2021-08-16",
        }
        response = requests.post(url, headers=headers)
        if response.status_code == 401:
            raise ValueError(f"The provided API token is invalid")
        if response.status_code == 404:
            raise ValueError(f"Unable to find database with id '{database_id}'")
        if response.status_code == 400:
            raise ValueError(f"Invalid request")
        if response.status_code != 200:
            raise ValueError(f"Unable to find database with id '{database_id}'")
        return response.json()


def id_from_share_link(share_link):
    hyphens_removed = share_link.replace("-", "")
    if not hyphens_removed.startswith("https://www.notion.so/"):
        return hyphens_removed
    else:
        return hyphens_removed.split("/")[-1].split("?")[0]

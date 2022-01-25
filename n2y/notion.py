"""
Grabbing data from the Notion API
"""
import requests


class Client:
    def __init__(self, access_token):
        self.access_token = access_token
        self.base_url = "https://api.notion.com/v1/"
        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "Notion-Version": "2021-08-16",
        }

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
        response = requests.post(url, headers=self.headers)
        if response.status_code == 401:
            raise ValueError("The provided API token is invalid")
        if response.status_code == 404:
            raise ValueError(f"Unable to find database with id '{database_id}'")
        if response.status_code == 400:
            raise ValueError("Invalid request")
        if response.status_code != 200:
            raise ValueError(f"Unable to find database with id '{database_id}'")
        return response.json()

    # recursively get block children
    def get_block_children(self, block_id, recursive=False):
        starting_url = f"{self.base_url}blocks/{block_id}/children"

        # Blocks that may have children.
        # https://developers.notion.com/reference/block
        blocks_to_expand = [
            "paragraph",
            "callout",
            "quote",
            "bulleted_list_item",
            "numbered_list_item",
            "to_do",
            "toggle",
            "column_list",
            "column",
            "template",
            "synced_block",
            "table",
        ]

        def depaginator(url):
            while True:
                data = self._get_block_children(url, block_id)
                yield data["results"]
                if not data["has_more"]:
                    return
                else:
                    url = data["next_cursor"]

        result = sum(depaginator(starting_url), [])

        # recurse for all blocks that have children
        if recursive:
            for item in result:
                if item['has_children'] and item['type'] in blocks_to_expand:
                    # populate child objects
                    item['children'] = self.get_block_children(item['id'])

        return result

    def _get_block_children(self, url, block_id):
        response = requests.get(url, headers=self.headers)
        if response.status_code == 401:
            raise ValueError("The provided API token is invalid")
        if response.status_code == 404:
            raise ValueError(f"Unable to find page with id '{block_id}'")
        if response.status_code == 400:
            raise ValueError("Invalid request")
        if response.status_code != 200:
            raise ValueError(f"Unable to find page with id '{block_id}'")

        return response.json()

    def get_page(self, page_id):
        page = self.get_block_children(page_id)
        return page

    def get_block(self, block_id):
        url = f"{self.base_url}blocks/{block_id}"
        response = requests.get(url, headers=self.headers)
        if response.status_code == 401:
            raise ValueError("The provided API token is invalid")
        if response.status_code == 404:
            raise ValueError(f"Unable to find block with id '{block_id}'")
        if response.status_code == 400:
            raise ValueError("Invalid request")
        if response.status_code != 200:
            raise ValueError(f"Unable to find block with id '{block_id}'")

        return response.json()


def id_from_share_link(share_link):
    hyphens_removed = share_link.replace("-", "")
    if not hyphens_removed.startswith("https://www.notion.so/"):
        return hyphens_removed
    else:
        return hyphens_removed.split("/")[-1].split("?")[0]

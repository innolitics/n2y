"""
Grabbing data from the Notion API
"""
import logging

import requests

from .errors import HTTPResponseError, APIResponseError, is_api_error_code, APIErrorCode


logger = logging.getLogger(__name__)


class Client:
    def __init__(self, access_token):
        self.access_token = access_token
        self.base_url = "https://api.notion.com/v1/"
        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "Notion-Version": "2021-08-16",
        }

    def get_page_or_database(self, object_id):
        """
        First attempt to get the page corresponding with the object id; if
        the page doesn't exist, then attempt to retrieve the database. This
        trial-and-error is necessary because the API doesn't provide a means to
        determining what type of object corresponds with an ID and we don't want
        to make the user indicate if they are pulling down a database or a page.
        """
        try:
            return self.get_page(object_id), "page"
        except APIResponseError as e:
            if e.code == APIErrorCode.ObjectNotFound:
                return self.get_database(object_id), "database"
            else:
                raise e

    def get_database(self, database_id):
        starting_url = f"{self.base_url}databases/{database_id}/query"

        def depaginator(url):
            while True:
                data = self._post_url(url)
                yield data["results"]
                if not data["has_more"]:
                    return
                else:
                    url = data["next_cursor"]

        return sum(depaginator(starting_url), [])

    def get_page(self, page_id):
        return self._get_url(f"{self.base_url}pages/{page_id}")

    def get_block(self, block_id):
        url = f"{self.base_url}blocks/{block_id}"
        response = requests.get(url, headers=self.headers)
        return self._parse_response(response)

    def get_block_children(self, block_id, recursive=False):
        """Recursively get block children"""
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
                data = self._get_url(url)
                yield data["results"]
                if not data["has_more"]:
                    return
                else:
                    url = data["next_cursor"]

        result = sum(depaginator(starting_url), [])

        if recursive:
            for item in result:
                if item['has_children'] and item['type'] in blocks_to_expand:
                    item['children'] = self.get_block_children(item['id'])

        return result

    def _get_url(self, url):
        response = requests.get(url, headers=self.headers)
        return self._parse_response(response)

    def _post_url(self, url):
        response = requests.post(url, headers=self.headers)
        return self._parse_response(response)

    def _parse_response(self, response):
        """Taken from https://github.com/ramnes/notion-sdk-py"""
        try:
            response.raise_for_status()
        except requests.HTTPError as error:
            try:
                body = error.response.json()
                code = body.get("code")
            except json.JSONDecodeError:
                code = None
            if code and is_api_error_code(code):
                raise APIResponseError(response, body["message"], code)
            raise HTTPResponseError(error.response)
        body = response.json()
        logger.debug(f"=> %s", body)
        return body


def id_from_share_link(share_link):
    hyphens_removed = share_link.replace("-", "")
    if not hyphens_removed.startswith("https://www.notion.so/"):
        return hyphens_removed
    else:
        return hyphens_removed.split("/")[-1].split("?")[0]

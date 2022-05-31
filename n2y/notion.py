"""
Grabbing data from the Notion API
"""
import logging
import json
from os import path, makedirs
from shutil import copyfileobj
from urllib.parse import urlparse, urljoin

import requests

from n2y.errors import HTTPResponseError, APIResponseError, is_api_error_code, APIErrorCode
from n2y.file import File
from n2y.page import Page
from n2y.database import Database
from n2y.blocks import DEFAULT_BLOCKS
from n2y.properties import DEFAULT_PROPERTIES
from n2y.property_values import DEFAULT_PROPERTY_VALUES
from n2y.user import User
from n2y.rich_text import RichTextArray


logger = logging.getLogger(__name__)


class Client:
    """
    An instance of the client class has a few purposes:
    1. To store configuration
    2. To retrieve data from Notion
    3. To determine what classes to use to wrap this notion data, based on the configuration
    4. To act as a shared global store for all of the objects that are pulled
       from Notion (e.g., there may be a lookup table between notion page IDs and
       local file names so that links can be translated)
    """

    def __init__(self, access_token, media_root='.', media_url=''):
        self.access_token = access_token
        self.media_root = media_root
        self.media_url = media_url
        self.base_url = "https://api.notion.com/v1/"
        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-02-22",
        }
        self.page_class = Page
        self.database_class = Database
        self.block_classes = DEFAULT_BLOCKS
        self.property_classes = DEFAULT_PROPERTIES
        self.property_value_classes = DEFAULT_PROPERTY_VALUES
        self.user_class = User
        self.file_class = File
        self.rich_text_array_class = RichTextArray

    def wrap_notion_page(self, notion_data, parent=None):
        return self.page_class(self, notion_data, parent)

    def wrap_notion_database(self, notion_data, parent=None):
        return self.database_class(self, notion_data, parent)

    def wrap_notion_user(self, notion_data):
        return self.user_class(self, notion_data)

    def wrap_notion_file(self, notion_data):
        return self.file_class(self, notion_data)

    def wrap_notion_rich_text_array(self, notion_data):
        return self.rich_text_array_class(self, notion_data)

    def wrap_notion_property(self, notion_data):
        notion_property_type = notion_data["type"]
        property_class = self.property_classes.get(notion_property_type, None)
        if property_class:
            return property_class(self, notion_data)
        else:
            raise NotImplementedError(f'Unknown property type: "{notion_property_type}"')

    def wrap_notion_property_value(self, notion_data):
        notion_property_value_type = notion_data["type"]
        property_value_class = self.property_value_classes.get(notion_property_value_type, None)
        if property_value_class:
            return property_value_class(self, notion_data)
        else:
            msg = f'Unknown property value type: "{notion_property_value_type}"'
            raise NotImplementedError(msg)

    def get_page_or_database(self, object_id):
        """
        First attempt to get the page corresponding with the object id; if
        the page doesn't exist, then attempt to retrieve the database. This
        trial-and-error is necessary because the API doesn't provide a means to
        determining what type of object corresponds with an ID and we don't want
        to make the user indicate if they are pulling down a database or a page.
        """
        try:
            return self.get_page(object_id)
        except APIResponseError as e:
            if e.code == APIErrorCode.ObjectNotFound:
                return self.get_database(object_id)
            else:
                raise e

    def get_database(self, database_id, parent=None):
        notion_database = self._get_url(f"{self.base_url}databases/{database_id}")
        return self.wrap_notion_database(notion_database, parent)

    def get_database_pages(self, database_id, parent):
        notion_pages = self.get_database_notion_pages(database_id)
        return [self.wrap_notion_page(np, parent) for np in notion_pages]

    def get_database_notion_pages(self, database_id):
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

    def get_page(self, page_id, parent=None):
        notion_page = self._get_url(f"{self.base_url}pages/{page_id}")
        return self.wrap_notion_page(notion_page, parent)

    def get_block(self, block_id, get_children=True):
        notion_block = self.get_notion_block(block_id)
        return self._wrap_notion_block(notion_block, get_children)

    def _wrap_notion_block(self, notion_block, get_children):
        notion_block_type = notion_block["type"]
        block_class = self.block_classes.get(notion_block_type, None)
        if block_class:
            return block_class(self, notion_block, get_children)
        else:
            raise NotImplementedError(f'Unknown block type: "{notion_block_type}"')

    def get_notion_block(self, block_id):
        url = f"{self.base_url}blocks/{block_id}"
        response = requests.get(url, headers=self.headers)
        return self._parse_response(response)

    def get_child_blocks(self, block_id, get_children):
        child_notion_blocks = self.get_child_notion_blocks(block_id)
        return [self._wrap_notion_block(b, get_children) for b in child_notion_blocks]

    def get_child_notion_blocks(self, block_id):
        starting_url = f"{self.base_url}blocks/{block_id}/children"

        def depaginator(url):
            while True:
                data = self._get_url(url)
                yield data["results"]
                if not data["has_more"]:
                    return
                else:
                    cursor = data["next_cursor"]
                    url = f"{starting_url}?start_cursor={cursor}"

        return sum(depaginator(starting_url), [])

    def get_page_property(self, page_id, property_id):
        notion_property = self.get_notion_page_property(page_id, property_id)
        return self.wrap_notion_property(notion_property)

    def get_notion_page_property(self, page_id, property_id):
        url = f"{self.base_url}pages/{page_id}/properties/{property_id}"
        response = requests.get(url, headers=self.headers)
        return self._parse_response(response)

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
        return response.json()

    def download_file(self, url):
        # TODO: append created time as hex to end of file to prevent collisions?
        makedirs(self.media_root, exist_ok=True)
        url_path = path.basename(urlparse(url).path)
        local_filename = path.join(self.media_root, url_path)
        with requests.get(url, stream=True) as request_stream:
            with open(local_filename, 'wb') as file_stream:
                copyfileobj(request_stream.raw, file_stream)
        return urljoin(self.media_url, url_path)


def id_from_share_link(share_link):
    hyphens_removed = share_link.replace("-", "")
    if not hyphens_removed.startswith("https://www.notion.so/"):
        return hyphens_removed
    else:
        return hyphens_removed.split("/")[-1].split("?")[0]

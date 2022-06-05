import copy
import logging
import json
from os import path, makedirs
from shutil import copyfileobj
from urllib.parse import urljoin
import importlib.util

import requests

from n2y.errors import (
    HTTPResponseError, APIResponseError, PluginError, is_api_error_code,
    APIErrorCode
)
from n2y.file import File
from n2y.page import Page
from n2y.database import Database
from n2y.blocks import DEFAULT_BLOCKS
from n2y.properties import DEFAULT_PROPERTIES
from n2y.property_values import DEFAULT_PROPERTY_VALUES
from n2y.user import User
from n2y.rich_text import DEFAULT_RICH_TEXTS, RichTextArray
from n2y.mentions import DEFAULT_MENTIONS


DEFAULT_NOTION_CLASSES = {
    "page": Page,
    "database": Database,
    "blocks": DEFAULT_BLOCKS,
    "properties": DEFAULT_PROPERTIES,
    "property_values": DEFAULT_PROPERTY_VALUES,
    "user": User,
    "file": File,
    "rich_text_array": RichTextArray,
    "rich_texts": DEFAULT_RICH_TEXTS,
    "mentions": DEFAULT_MENTIONS,
}


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

    def __init__(self, access_token, media_root='.', media_url='', plugins=None):
        self.access_token = access_token
        self.media_root = media_root
        self.media_url = media_url
        self.base_url = "https://api.notion.com/v1/"
        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-02-22",
        }

        self.notion_classes = copy.deepcopy(DEFAULT_NOTION_CLASSES)
        self.load_plugins(plugins)
        self.plugin_data = {}

    def load_plugins(self, plugins):
        if plugins is not None:
            for plugin in plugins:
                plugin_module = importlib.import_module(plugin)
                try:
                    self.load_plugin(plugin_module.notion_classes)
                except PluginError as err:
                    logger.error('Error loading plugin "%s": %s', plugin, err)
                    raise

    def load_plugin(self, notion_classes):
        for notion_object, object_types in notion_classes.items():
            if notion_object in self.notion_classes:
                default_object_types = DEFAULT_NOTION_CLASSES[notion_object]
                self._override_notion_classes(notion_object, object_types, default_object_types)
            else:
                raise PluginError(f'Invalid notion object "{notion_object}"')

    def _override_notion_classes(self, notion_object, object_types, default_object_types):
        # E.g., there are many types of notion blocks but only one type of notion page.
        notion_object_has_types = isinstance(default_object_types, dict)

        if notion_object_has_types and isinstance(object_types, dict):
            for object_type, plugin_class in object_types.items():
                if object_type in default_object_types:
                    class_being_replaced = default_object_types[object_type]
                    # assumes all of the default classes have a single parent class
                    base_class = class_being_replaced.__bases__[0]
                    if issubclass(plugin_class, base_class):
                        self.notion_classes[notion_object][object_type] = plugin_class
                    else:
                        raise PluginError(
                            f'Cannot use "{plugin_class.__name__}", as it doesn\'t '
                            f'override the base class "{base_class.__name__}"',
                        )
                else:
                    raise PluginError(f'Invalid type "{object_type}" for "{notion_object}"')
        elif notion_object_has_types and not isinstance(object_types, dict):
            raise PluginError(
                f'Expecting a dict for "{notion_object}", found "{type(object_types)}"')
        else:
            plugin_class = object_types
            base_class = default_object_types
            if issubclass(plugin_class, base_class):
                self.notion_classes[notion_object] = plugin_class
            else:
                raise PluginError(
                    f'Cannot use "{plugin_class.__name__}", as it doesn\'t '
                    f'override the base class "{base_class.__name__}"',
                )

    def get_class(self, notion_object, object_type=None):
        if object_type is None:
            return self.notion_classes[notion_object]
        try:
            return self.notion_classes[notion_object][object_type]
        except KeyError:
            raise NotImplementedError(f'Unknown "{notion_object}" class of type "{object_type}"')

    def wrap_notion_page(self, notion_data, parent=None):
        page_class = self.get_class("page")
        return page_class(self, notion_data, parent)

    def wrap_notion_database(self, notion_data, parent=None):
        database_class = self.get_class("database")
        return database_class(self, notion_data, parent)

    def wrap_notion_block(self, notion_data, get_children):
        block_class = self.get_class("blocks", notion_data["type"])
        return block_class(self, notion_data, get_children)

    def wrap_notion_user(self, notion_data):
        user_class = self.get_class("user")
        return user_class(self, notion_data)

    def wrap_notion_file(self, notion_data):
        file_class = self.get_class("file")
        return file_class(self, notion_data)

    def wrap_notion_rich_text_array(self, notion_data):
        rich_text_array_class = self.get_class("rich_text_array")
        return rich_text_array_class(self, notion_data)

    def wrap_notion_rich_text(self, notion_data):
        rich_text_class = self.get_class("rich_texts", notion_data["type"])
        return rich_text_class(self, notion_data)

    def wrap_notion_mention(self, notion_data):
        mention_class = self.get_class("mentions", notion_data["type"])
        return mention_class(self, notion_data)

    def wrap_notion_property(self, notion_data):
        property_class = self.get_class("properties", notion_data["type"])
        return property_class(self, notion_data)

    def wrap_notion_property_value(self, notion_data):
        property_value_class = self.get_class("property_values", notion_data["type"])
        return property_value_class(self, notion_data)

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
                pass
            else:
                raise e
        return self.get_database(object_id)

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
        return self.wrap_notion_block(notion_block, get_children)

    def get_notion_block(self, block_id):
        url = f"{self.base_url}blocks/{block_id}"
        response = requests.get(url, headers=self.headers)
        return self._parse_response(response)

    def get_child_blocks(self, block_id, get_children):
        child_notion_blocks = self.get_child_notion_blocks(block_id)
        return [self.wrap_notion_block(b, get_children) for b in child_notion_blocks]

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

    def download_file(self, url, file_path):
        # TODO: append created time as hex to end of file to prevent collisions?
        local_filename = path.join(self.media_root, file_path)
        makedirs(path.dirname(local_filename), exist_ok=True)
        with requests.get(url, stream=True) as request_stream:
            with open(local_filename, 'wb') as file_stream:
                copyfileobj(request_stream.raw, file_stream)
        return urljoin(self.media_url, file_path)


def id_from_share_link(share_link):
    hyphens_removed = share_link.replace("-", "")
    if not hyphens_removed.startswith("https://www.notion.so/"):
        return hyphens_removed
    else:
        return hyphens_removed.split("/")[-1].split("?")[0]

import hashlib
import logging
import json
from os import path, makedirs
import os
import shutil
import tempfile
from urllib.parse import urljoin, urlparse
import importlib.util

import requests

from n2y.errors import (
    HTTPResponseError, APIResponseError, ObjectNotFound, PluginError,
    UseNextClass, is_api_error_code, APIErrorCode
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
from n2y.utils import strip_hyphens


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

# TODO: Rename this file `client.py`


class Client:
    """
    An instance of the client class has a few purposes:

    1. To store configuration
    2. To retrieve data from Notion
    3. To determine what classes to use to wrap this notion data, based on the configuration
    4. To act as a shared global store for all of the objects that are pulled
       from Notion.

    In particular there is a cache of all pages and databases which ensure that
    the database class and page class are instantiated exactly once for each
    page or database.
    """

    def __init__(
        self,
        access_token,
        media_root='.',
        media_url='',
        plugins=None,
        content_property=None,
        id_property=None,
        url_property=None,
        filename_property=None,
        database_config=None,
    ):
        self.access_token = access_token
        self.media_root = media_root
        self.media_url = media_url
        self.content_property = content_property
        self.id_property = id_property
        self.url_property = url_property
        self.filename_property = filename_property
        self.database_config = database_config if database_config is not None else {}

        self.base_url = "https://api.notion.com/v1/"
        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-02-22",
        }

        self.databases_cache = {}
        self.pages_cache = {}

        self.notion_classes = self.get_default_classes()
        self.load_plugins(plugins)
        self.plugin_data = {}

    def get_default_classes(self):
        notion_classes = {}
        for notion_object, object_types in DEFAULT_NOTION_CLASSES.items():
            if type(object_types) == dict:
                notion_classes[notion_object] = {k: [v] for k, v in object_types.items()}
            else:
                notion_classes[notion_object] = [object_types]
        return notion_classes

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
                        self.notion_classes[notion_object][object_type].append(plugin_class)
                    else:
                        raise PluginError(
                            f'Cannot use "{plugin_class.__name__}", as it doesn\'t '
                            f'override the base class "{base_class.__name__}"',
                        )
                else:
                    raise PluginError(f'Invalid type "{object_type}" for "{notion_object}"')
        elif notion_object_has_types and not isinstance(object_types, dict):
            raise PluginError(f'Expecting dict for "{notion_object}", found "{type(object_types)}"')
        else:
            plugin_class = object_types
            base_class = default_object_types
            if issubclass(plugin_class, base_class):
                self.notion_classes[notion_object].append(plugin_class)
            else:
                raise PluginError(
                    f'Cannot use "{plugin_class.__name__}", as it doesn\'t '
                    f'override the base class "{base_class.__name__}"',
                )

    def get_class_list(self, notion_object, object_type=None):
        if object_type is None:
            return self.notion_classes[notion_object]
        try:
            return self.notion_classes[notion_object][object_type]
        except KeyError:
            raise NotImplementedError(f'Unknown "{notion_object}" class of type "{object_type}"')

    def instantiate_class(self, notion_object, object_type, *args, **kwargs):
        class_list = self.get_class_list(notion_object, object_type)
        for klass in reversed(class_list):
            try:
                return klass(*args, **kwargs)
            except UseNextClass:
                logger.debug("Skipping %s due to UseNextClass exception", klass.__name__)

    def _wrap_notion_page(self, notion_data):
        """
        Wrap notion page data in the appropriate class. If the page class has
        already been created, then ignore the new notion data and just return
        the existing version.

        Note that it may seem redundant to check the cache here, since it's also
        checked in `get_page`, however unlike databases which are only ever
        retrieved via `get_database`, pages can be retrieved either through
        `get_page` or through `get_database_pages`. Thus, it's possible that a
        database page be first retrieved individually and then retrieved via the
        full database. In this case, it's unfortunate (but unavoidable) that we
        retrieved the data from Notion twice, but even so we don't want to
        replace our existing page instance, along with it's content or other
        state that has been added to it.
        """
        if notion_data["id"] in self.pages_cache:
            return self.pages_cache[notion_data["id"]]
        else:
            page = self.instantiate_class("page", None, self, notion_data)
            self.pages_cache[page.notion_id] = page
            return page

    def _wrap_notion_database(self, notion_data):
        return self.instantiate_class("database", None, self, notion_data)

    def wrap_notion_block(self, notion_data, page, get_children):
        return self.instantiate_class(
            "blocks", notion_data["type"],
            self, notion_data, page, get_children,
        )

    def wrap_notion_user(self, notion_data):
        return self.instantiate_class("user", None, self, notion_data)

    def wrap_notion_file(self, notion_data):
        return self.instantiate_class("file", None, self, notion_data)

    def wrap_notion_rich_text_array(self, notion_data, block=None):
        return self.instantiate_class("rich_text_array", None, self, notion_data, block)

    def wrap_notion_rich_text(self, notion_data, block=None):
        return self.instantiate_class("rich_texts", notion_data["type"], self, notion_data, block)

    def wrap_notion_mention(self, notion_data, plain_text, block=None):
        # here we pass in the plain_text to avoid the need to query the page
        # just to get its title
        return self.instantiate_class(
            "mentions", notion_data["type"],
            self, notion_data, plain_text, block,
        )

    def wrap_notion_property(self, notion_data):
        return self.instantiate_class("properties", notion_data["type"], self, notion_data)

    def wrap_notion_property_value(self, notion_data):
        return self.instantiate_class("property_values", notion_data["type"], self, notion_data)

    def get_page_or_database(self, object_id):
        """
        First attempt to get the page corresponding with the object id; if
        the page doesn't exist, then attempt to retrieve the database. This
        trial-and-error is necessary because the API doesn't provide a means to
        determining what type of object corresponds with an ID and we don't want
        to make the user indicate if they are pulling down a database or a page.
        """
        page = self.get_page(object_id)
        if page is not None:
            return page
        else:
            return self.get_database(object_id)

    def get_database(self, database_id):
        """
        Retrieve the database (but not it's pages) if its not in the cache. Even
        if it is in the cache.
        """
        if database_id in self.databases_cache:
            database = self.databases_cache[database_id]
        else:
            try:
                notion_database = self._get_url(f"{self.base_url}databases/{database_id}")
                database = self._wrap_notion_database(notion_database)
            except ObjectNotFound:
                database = None
            self.databases_cache[database_id] = database
        return database

    def get_database_pages(self, database_id):
        notion_pages = self.get_database_notion_pages(database_id)
        return [self._wrap_notion_page(np) for np in notion_pages]

    def get_database_notion_pages(self, database_id):
        results = []
        url = f"{self.base_url}databases/{database_id}/query"
        request_data = self._create_database_request_data(database_id)
        while True:
            data = self._post_url(url, request_data)
            results.extend(data["results"])
            if not data["has_more"]:
                return results
            else:
                request_data["start_cursor"] = data["next_cursor"]

    def _create_database_request_data(self, database_id):
        stripped_database_id = strip_hyphens(database_id)
        return self.database_config.get(stripped_database_id, {})

    def get_page(self, page_id):
        """
        Retrieve the page if its not in the cache.
        """
        if page_id in self.pages_cache:
            page = self.pages_cache[page_id]
        else:
            try:
                notion_page = self._get_url(f"{self.base_url}pages/{page_id}")
            except ObjectNotFound:
                self.pages_cache[page_id] = None
                return
            # _wrap_notion_page will add the page to the cache
            page = self._wrap_notion_page(notion_page)
        return page

    def get_block(self, block_id, page, get_children=True):
        notion_block = self.get_notion_block(block_id)
        return self.wrap_notion_block(notion_block, page, get_children)

    def get_notion_block(self, block_id):
        url = f"{self.base_url}blocks/{block_id}"
        response = requests.get(url, headers=self.headers)
        return self._parse_response(response)

    def get_child_blocks(self, block_id, page, get_children):
        child_notion_blocks = self.get_child_notion_blocks(block_id)
        return [self.wrap_notion_block(b, page, get_children) for b in child_notion_blocks]

    def get_child_notion_blocks(self, block_id):
        url = f"{self.base_url}blocks/{block_id}/children"
        params = {}
        results = []
        while True:
            data = self._get_url(url, params)
            results.extend(data["results"])
            if not data["has_more"]:
                return results
            else:
                params["start_cursor"] = data["next_cursor"]

    def get_page_property(self, page_id, property_id):
        notion_property = self.get_notion_page_property(page_id, property_id)
        return self.wrap_notion_property(notion_property)

    def get_notion_page_property(self, page_id, property_id):
        url = f"{self.base_url}pages/{page_id}/properties/{property_id}"
        response = requests.get(url, headers=self.headers)
        return self._parse_response(response)

    def _get_url(self, url, params=None):
        if params is None:
            params = {}
        response = requests.get(url, headers=self.headers, params=params)
        return self._parse_response(response)

    def _post_url(self, url, data=None):
        if data is None:
            data = {}
        response = requests.post(url, headers=self.headers, json=data)
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
            if code == APIErrorCode.ObjectNotFound:
                raise ObjectNotFound(response, body["message"])
            elif code and is_api_error_code(code):
                raise APIResponseError(response, body["message"], code)
            raise HTTPResponseError(error.response)
        return response.json()

    def download_file(self, url, page):
        """
        Download a file from a given URL into the MEDIA_ROOT.

        Preserve the file extension from the URL, but use the name of the parent
        page followed by an md5 hash.
        """
        url_path = path.basename(urlparse(url).path)
        _, extension = path.splitext(url_path)
        with requests.get(url, stream=True) as request_stream:
            content_iterator = request_stream.iter_content(4096)
            return self.save_file(content_iterator, page, extension)

    def save_file(self, content_iterator, page, extension):
        """
        Save the content in the provided iterator into a file in MEDIA_ROOT. The
        file name is determined from the page name, file extension, and an md5
        hash of the content. The md5 hash is calculated as the data is streamed
        to a temporary file, which is then moved to the final location once the
        md5 hash can be calculated.
        """
        temp_fd, temp_filepath = tempfile.mkstemp()
        hash_md5 = hashlib.md5()
        with os.fdopen(temp_fd, 'wb') as temp_file:
            for chunk in content_iterator:
                hash_md5.update(chunk)
                temp_file.write(chunk)

        num_hash_characters = 8  # just long enough to avoid collisions
        hash = hash_md5.hexdigest()[:num_hash_characters]
        relative_filepath = "".join([page.filename, "-", hash, extension])
        full_filepath = path.join(self.media_root, relative_filepath)

        makedirs(path.dirname(full_filepath), exist_ok=True)
        shutil.move(temp_filepath, full_filepath)
        return urljoin(self.media_url, relative_filepath)

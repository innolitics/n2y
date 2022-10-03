import logging
import json
from os import path, makedirs
from urllib.parse import urljoin, urlparse
import importlib.util

import requests

from n2y.user import User
from n2y.file import File
from n2y.page import Page
from n2y.emoji import Emoji
from n2y.comment import Comment
from n2y.database import Database
from n2y.blocks import DEFAULT_BLOCKS
from n2y.mentions import DEFAULT_MENTIONS
from n2y.properties import DEFAULT_PROPERTIES
from n2y.utils import sanitize_filename, strip_hyphens
from n2y.property_values import DEFAULT_PROPERTY_VALUES
from n2y.rich_text import DEFAULT_RICH_TEXTS, RichTextArray
from n2y.errors import (
    HTTPResponseError, APIResponseError, ObjectNotFound, PluginError,
    UseNextClass, UseNextType, is_api_error_code, APIErrorCode
)


DEFAULT_NOTION_CLASSES = {
    "property_values": DEFAULT_PROPERTY_VALUES,
    "rich_texts": DEFAULT_RICH_TEXTS,
    "properties": DEFAULT_PROPERTIES,
    "rich_text_array": RichTextArray,
    "mentions": DEFAULT_MENTIONS,
    "blocks": DEFAULT_BLOCKS,
    "database": Database,
    "comment": Comment,
    "emoji": Emoji,
    "user": User,
    "page": Page,
    "file": File,
}


logger = logging.getLogger(__name__)

# TODO: Rename this file `client.py`


class Client:
    """
    An instance of the client class has a few purposes:

    1. To retrieve data from Notion
    2. To determine what classes to use to wrap this notion data
    3. To act as a shared global store for all of the objects that are pulled
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
    ):
        self.access_token = access_token
        self.media_root = media_root
        self.media_url = media_url

        self.base_url = "https://api.notion.com/v1/"
        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28",
        }

        self.databases_cache = {}
        self.pages_cache = {}

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
        self.notion_classes = self.get_default_classes()
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

    def instantiate_class(self, *args, **kwargs):
        first_arg = args[0]
        if type(first_arg) == str:
            return self._instantiate_class_from_notion(first_arg, args[1], *args[2:])
        else:
            return self._instantiate_class_from_pandoc(first_arg, args[1], **kwargs)

    def _instantiate_class_from_notion(self, notion_object, object_type, *args, **kwargs):
        class_list = self.get_class_list(notion_object, object_type)
        for klass in reversed(class_list):
            try:
                return klass(*args, **kwargs)
            except UseNextClass:
                logger.debug("Skipping %s due to UseNextClass exception", klass.__name__)

    def _instantiate_class_from_pandoc(self, pandoc_ast, page, **kwargs):
        for pandoc_type, pandoc_type_info in PANDOC_TYPES.items():
            try:
                if type(pandoc_ast) in pandoc_type_info["pandoc"]:
                    mock_data, children = \
                        pandoc_type_info["parse_pandoc"](pandoc_ast, self, page)
                    notion_data = mock_block(pandoc_type, mock_data)
                    class_args = [self, notion_data, page]
                    new_block = pandoc_type_info["class"](*class_args, **kwargs)
                    new_block.has_children = bool(children)
                    new_block._children = children
                    return new_block
                else:
                    raise UseNextType()
            except UseNextType:
                logger.debug("Skipping %s due to UseNextType exception", pandoc_type)

    def _process_pandoc_children(self, pandoc_children, page):
        class_children = []
        for pandoc_child in pandoc_children:
            class_child = self.instantiate_class(pandoc_child, page)
            class_children.append(class_child)
        return class_children

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

    def wrap_notion_emoji(self, notion_data):
        return self.instantiate_class("emoji", None, self, notion_data)

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

    def get_database_pages(self, database_id, filter=None, sorts=None):
        notion_pages = self.get_database_notion_pages(database_id, filter, sorts)
        return [self._wrap_notion_page(np) for np in notion_pages]

    def get_database_notion_pages(self, database_id, filter, sorts):
        url = f"{self.base_url}databases/{database_id}/query"
        request_data = {}
        if filter:
            request_data["filter"] = filter
        if sorts:
            request_data["sorts"] = sorts
        return self._paginated_request(self._post_url, url, request_data)

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
        return self._paginated_request(self._get_url, url, {})

    def get_comments(self, block_id):
        url = f"{self.base_url}comments"
        comments = self._paginated_request(self._get_url, url, {"block_id": block_id})
        return [self.wrap_notion_comment(nd) for nd in comments]

    def wrap_notion_comment(self, notion_data):
        return self.instantiate_class("comment", None, self, notion_data)

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

    def _paginated_request(self, request_method, url, initial_params):
        params = initial_params
        results = []
        while True:
            data = request_method(url, params)
            results.extend(data["results"])
            if not data["has_more"]:
                return results
            else:
                params["start_cursor"] = data["next_cursor"]

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
        request_stream = requests.get(url, stream=True)
        return self.save_file(request_stream.content, page, extension)

    def save_file(self, content, page, extension):
        page_id_chars = strip_hyphens(page.notion_id)
        page_title = sanitize_filename(page.title.to_plain_text())
        relative_filepath = f"{page_title}-{page_id_chars[:11]}{extension}"
        full_filepath = path.join(self.media_root, relative_filepath)
        makedirs(self.media_root, exist_ok=True)
        with open(full_filepath, 'wb') as temp_file:
            temp_file.write(content)
        return urljoin(self.media_url, relative_filepath)

    def append_block_children(self, block_id, children):
        response = requests.patch(
            f"{self.base_url}blocks/{block_id}/children",
            json={"children": children}, headers=self.headers
        )
        return self._parse_response(response)

    def delete_block(self, block_id):
        headers = {**self.headers}
        del headers['Content-Type']
        response = requests.delete(
            f"{self.base_url}blocks/{block_id}", headers=headers
        )
        return self._parse_response(response)

    def save_block(self, page, pandoc_ast):
        new_block = self.instantiate_class(pandoc_ast, page)
        self.store_unsaved_block(page, new_block)

    def store_unsaved_block(self, page, block):
        if 'unsaved_blocks' in self.__dict__:
            if page in self.unsaved_blocks:
                self.unsaved_blocks[page].append(block)
            else:
                self.unsaved_blocks[page] = [block]
        else:
            self.unsaved_blocks = {page: [block]}

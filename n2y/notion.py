import importlib.util
import json
import logging
from os import makedirs, path
from urllib.parse import urljoin, urlparse

import requests

from n2y.blocks import DEFAULT_BLOCKS
from n2y.comment import Comment
from n2y.config import merge_default_config
from n2y.database import Database
from n2y.emoji import Emoji
from n2y.errors import (
    APIErrorCode,
    APIResponseError,
    ConnectionThrottled,
    HTTPResponseError,
    ObjectNotFound,
    PluginError,
    UseNextClass,
)
from n2y.file import File
from n2y.mentions import DEFAULT_MENTIONS
from n2y.notion_mocks import mock_rich_text_array
from n2y.page import Page
from n2y.properties import DEFAULT_PROPERTIES
from n2y.property_values import DEFAULT_PROPERTY_VALUES
from n2y.rich_text import DEFAULT_RICH_TEXTS, RichTextArray
from n2y.user import User
from n2y.utils import retry_api_call, sanitize_filename, strip_hyphens

# TODO: Rename this file `client.py`
log = logging.getLogger(__name__)

DEFAULT_NOTION_CLASSES = {
    "page": Page,
    "database": Database,
    "blocks": DEFAULT_BLOCKS,
    "properties": DEFAULT_PROPERTIES,
    "property_values": DEFAULT_PROPERTY_VALUES,
    "user": User,
    "file": File,
    "emoji": Emoji,
    "rich_text_array": RichTextArray,
    "rich_texts": DEFAULT_RICH_TEXTS,
    "mentions": DEFAULT_MENTIONS,
    "comment": Comment,
}


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
        media_root=".",
        media_url="",
        plugins=None,
        export_defaults=None,
        logger=log,
        retry=True,
    ):
        self.access_token = access_token
        self.media_root = media_root
        self.media_url = media_url
        self.logger = logger
        self.retry = retry
        self.export_defaults = export_defaults or merge_default_config({})

        self.base_url = "https://api.notion.com/v1/"
        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28",
        }

        self.databases_cache = {}
        self.pages_cache = {}
        self.users_cache = {}

        self.load_plugins(plugins)
        self.plugin_data = {}

    def get_default_classes(self):
        notion_classes = {}
        for notion_object, object_types in DEFAULT_NOTION_CLASSES.items():
            if type(object_types) is dict:
                notion_classes[notion_object] = {
                    k: [v] for k, v in object_types.items()
                }
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
                    self.logger.error('Error loading plugin "%s": %s', plugin, err)
                    raise

    def load_plugin(self, notion_classes):
        for notion_object, object_types in notion_classes.items():
            if notion_object in self.notion_classes:
                default_object_types = DEFAULT_NOTION_CLASSES[notion_object]
                self._override_notion_classes(
                    notion_object, object_types, default_object_types
                )
            else:
                raise PluginError(f'Invalid notion object "{notion_object}"')

    def _override_notion_classes(
        self, notion_object, object_types, default_object_types
    ):
        # E.g., there are many types of notion blocks but only one type of notion page.
        notion_object_has_types = isinstance(default_object_types, dict)

        if notion_object_has_types and isinstance(object_types, dict):
            for object_type, plugin_class in object_types.items():
                self._organize_notion_classes(
                    default_object_types, notion_object, object_type, plugin_class
                )
        elif notion_object_has_types and not isinstance(object_types, dict):
            raise PluginError(
                f'Expecting dict for "{notion_object}", found "{type(object_types)}"'
            )
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

    def _organize_notion_classes(
        self, default_object_types, notion_object, object_type, plugin_class
    ):
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

    def get_class_list(self, notion_object, object_type=None):
        if object_type is None:
            return self.notion_classes[notion_object]
        try:
            return self.notion_classes[notion_object][object_type]
        except KeyError:
            raise NotImplementedError(
                f'Unknown "{notion_object}" class of type "{object_type}"'
            )

    def instantiate_class(self, notion_object, object_type, *args, **kwargs):
        class_list = self.get_class_list(notion_object, object_type)
        for cls in reversed(class_list):
            try:
                return cls(*args, **kwargs)
            except UseNextClass:
                self.logger.debug(
                    "Skipping %s due to UseNextClass exception", cls.__name__
                )

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
        page_in_cache = notion_data["id"] in self.pages_cache
        if page_in_cache and self.class_is_in_use(
            # Need to check that the page in the client cache was instantiated using
            # the currently favored page class. Otherwise, plugins set for one export
            # will be used in another or a plugin will be set but not used.
            # As we currently use the `jinjarenderpage` plugin for all pages,
            # this check is most likely unnecessary at this point.
            self.pages_cache[notion_data["id"]],
            "page",
        ):
            return self.pages_cache[notion_data["id"]]
        else:
            page = self.instantiate_class("page", None, self, notion_data)
            not page_in_cache or self.logger.warning(
                f"page in cache overwritten at key \"{notion_data['id']}\""
            )
            self.pages_cache[page.notion_id] = page
            return page

    def _wrap_notion_database(self, notion_data):
        return self.instantiate_class("database", None, self, notion_data)

    def wrap_notion_block(self, notion_data, page, get_children):
        return self.instantiate_class(
            "blocks",
            notion_data["type"],
            self,
            notion_data,
            page,
            get_children,
        )

    def wrap_notion_user(self, notion_data):
        """
        Retrieve the user if its not in the cache.
        """
        user_id = notion_data["id"]
        if user_id in self.users_cache and self.class_is_in_use(
            self.users_cache[user_id], "user"
        ):
            user = self.users_cache[user_id]
        else:
            if [key for key in notion_data] == ["object", "id"]:
                try:
                    notion_data = self.get_notion_user(user_id)
                except ObjectNotFound:
                    pass
            user = self.instantiate_class("user", None, self, notion_data)
            self.users_cache[user_id] = user
        return user

    def wrap_notion_file(self, notion_data):
        return self.instantiate_class("file", None, self, notion_data)

    def wrap_notion_emoji(self, notion_data):
        return self.instantiate_class("emoji", None, self, notion_data)

    def wrap_notion_rich_text_array(self, notion_data, block=None):
        return self.instantiate_class("rich_text_array", None, self, notion_data, block)

    def wrap_notion_rich_text(self, notion_data, block=None):
        return self.instantiate_class(
            "rich_texts", notion_data["type"], self, notion_data, block
        )

    def wrap_notion_mention(self, notion_data, plain_text, block=None):
        # here we pass in the plain_text to avoid the need to query the page
        # just to get its title
        return self.instantiate_class(
            "mentions",
            notion_data["type"],
            self,
            notion_data,
            plain_text,
            block,
        )

    def wrap_notion_property(self, notion_data):
        return self.instantiate_class(
            "properties", notion_data["type"], self, notion_data
        )

    def wrap_notion_property_value(self, notion_data, page):
        return self.instantiate_class(
            "property_values", notion_data["type"], self, notion_data, page
        )

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
        if database_id in self.databases_cache and self.class_is_in_use(
            self.databases_cache[database_id], "database"
        ):
            database = self.databases_cache[database_id]
        else:
            try:
                notion_database = self.get_notion_database(database_id)
                database = self._wrap_notion_database(notion_database)
            except ObjectNotFound:
                database = None
            self.databases_cache[database_id] = database
        return database

    def get_notion_database(self, database_id):
        return self._get_url(f"{self.base_url}databases/{database_id}")

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
            if not self.class_is_in_use(page, "page"):
                page = self.instantiate_class("page", None, self, page.notion_data)
        else:
            try:
                notion_page = self.get_notion_page(page_id)
            except ObjectNotFound:
                self.pages_cache[page_id] = None
                return
            # _wrap_notion_page will add the page to the cache
            page = self._wrap_notion_page(notion_page)
        return page

    def get_notion_page(self, page_id):
        return self._get_url(f"{self.base_url}pages/{page_id}")

    def get_notion_user(self, user_id):
        return self._get_url(f"{self.base_url}users/{user_id}")

    def get_block(self, block_id, page, get_children=True):
        notion_block = self.get_notion_block(block_id)
        return self.wrap_notion_block(notion_block, page, get_children)

    def get_notion_block(self, block_id):
        url = f"{self.base_url}blocks/{block_id}"
        return self._get_url(url)

    def get_child_blocks(self, block_id, page, get_children):
        child_notion_blocks = self.get_child_notion_blocks(block_id)
        return [
            self.wrap_notion_block(b, page, get_children) for b in child_notion_blocks
        ]

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
        return self._get_url(url)

    def create_notion_page(self, page_data):
        creation_url = f"{self.base_url}pages"
        return self._post_url(creation_url, page_data)

    @retry_api_call
    def _get_url(self, url, params=None, stream=False):
        if not stream and params is None:
            params = {}
        response = requests.get(
            url,
            params=params,
            stream=stream,
            headers=self.headers if not stream else None,
        )
        return self._parse_response(response, stream)

    @retry_api_call
    def _post_url(self, url, data=None):
        if data is None:
            data = {}
        response = requests.post(url, headers=self.headers, json=data)
        return self._parse_response(response)

    @retry_api_call
    def _delete_url(self, url):
        response = requests.delete(
            url, headers={k: v for k, v in self.headers.items() if k != "Content-Type"}
        )
        return self._parse_response(response)

    @retry_api_call
    def _patch_url(self, url, data=None):
        if data is None:
            data = {}
        response = requests.patch(url, headers=self.headers, json=data)
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

    def _parse_response(self, response, stream=False):
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
            elif code == APIErrorCode.RateLimited:
                raise ConnectionThrottled(error.response)
            elif code and code in APIErrorCode:
                raise APIResponseError(response, body["message"], code)
            raise HTTPResponseError(error.response)
        return response.json() if not stream else response.content

    def download_file(self, url, page, block_id):
        """
        Download a file from a given URL into the MEDIA_ROOT.

        Preserve the file extension from the URL, but use the page title
        followed by a segment of the id of the block as the file name.
        """

        url_path = path.basename(urlparse(url).path)
        _, extension = path.splitext(url_path)
        content = self._get_url(url, stream=True)
        return self.save_file(content, page, extension, block_id)

    def save_file(self, content, page, extension, block_id):
        id_chars = strip_hyphens(block_id)
        page_title = sanitize_filename(page.title.to_plain_text())
        relative_filepath = f"{page_title}-{id_chars}{extension}"
        full_filepath = path.join(self.media_root, relative_filepath)
        makedirs(self.media_root, exist_ok=True)
        with open(full_filepath, "wb") as temp_file:
            temp_file.write(content)
        return urljoin(self.media_url, relative_filepath)

    def copy_notion_database_children(self, children, destination):
        """
        copy the notion children (`children`) of one notion database to another (`destination`)
        """
        bad_keys = [
            "id",
            "url",
            "parent",
            "created_by",
            "created_time",
            "last_edited_by",
            "last_edited_time",
        ]
        db_children = [
            {key: value for (key, value) in child.items() if key not in bad_keys}
            for child in children
        ]
        for page in db_children:
            page["parent"] = {"type": "database_id", "database_id": destination["id"]}
            for key in page["properties"].keys():
                page["properties"][key] = self._edit_notion_child_property(
                    page["properties"][key]
                )
            self.create_notion_page(page)

    def _edit_notion_child_property(self, prop):
        del prop["id"]
        prop_type = prop["type"]
        del prop["type"]
        prop_type_info = prop[prop_type]
        if isinstance(prop_type_info, dict):
            if "id" in prop_type_info:
                del prop_type_info["id"]
        elif isinstance(prop_type_info, list) and prop_type != "relation":
            for item in prop_type_info:
                if "id" in item:
                    del item["id"]
        return prop

    def _notion_block_type_is(self, block, type):
        return "type" in block and block["type"] == type

    def _notion_block_object_is(self, block, object):
        return "object" in block and block["object"] == object

    def append_child_notion_blocks(self, block_id, children):
        """
        Appends each datapoint of a list of notion_data as children to the block specified by id.
        Please note that not all block types are allowed to have children, so this method only works
        for those that are.
        """
        previous_i = 0
        children_appended = []
        parent = self.get_page_or_database(block_id) or self.get_block(block_id, None)
        parent_type = parent.notion_data["object"]

        for i, child in enumerate(children):
            if self._notion_block_object_is(
                child, "database"
            ) or self._notion_block_type_is(child, "child_database"):
                if previous_i != i:
                    children_appended = self._append_blocks(
                        block_id, children, children_appended, previous_i, i
                    )
                child_database = self._copy_notion_database_child_database(
                    parent, parent_type, child
                )
                children_appended.append(child_database)
                previous_i = i + 1
            elif self._notion_block_object_is(
                child, "page"
            ) or self._notion_block_type_is(child, "child_page"):
                if previous_i != i:
                    children_appended = self._append_blocks(
                        block_id, children, children_appended, previous_i, i
                    )
                child_page = self._copy_notion_database_child_page(
                    parent, parent_type, child
                )
                children_appended.append(child_page)
                previous_i = i + 1
            elif i == len(children) - 1:
                children_appended = self._append_blocks(
                    block_id, children, children_appended, previous_i, len(children)
                )
        return children_appended

    def _append_blocks(
        self, block_id, full_child_data_list, appension_history_list, i1=0, i2=0
    ):
        max_new_blocks = 100
        if i1 < i2:
            child_data_list = full_child_data_list[i1:i2]
            length = len(child_data_list)
            for i in range(0, length, max_new_blocks):
                portion_index_stop = i + max_new_blocks
                if portion_index_stop < length:
                    portion = child_data_list[i:portion_index_stop]
                else:
                    portion = child_data_list[i:]
                appension_return = self._patch_url(
                    f"{self.base_url}blocks/{block_id}/children", {"children": portion}
                )
                appension_history_list.extend(appension_return["results"])
        return appension_history_list

    def _copy_notion_database_child_page(self, parent, parent_type, child_notion_data):
        bad_keys = [
            "last_edited_by",
            "created_time",
            "last_edited_time",
            "created_by",
            "request_id",
        ]
        if parent_type == "block":
            self.logger.warning(
                "Skipping page with block type parent as "
                "appension is currently unsupported by Notion API"
            )
            child_page = {}
        else:
            page = self.get_page(child_notion_data["id"])
            child_page_data = {
                key: value
                for (key, value) in page.notion_data.items()
                if key not in bad_keys
            }
            child_page_data["parent"] = {
                "type": f"{parent_type}_id",
                f"{parent_type}_id": parent.notion_id,
            }
            child_page = self.create_notion_page(child_page_data)
        return child_page

    def _copy_notion_database_child_database(
        self, parent, parent_type, child_notion_data
    ):
        bad_keys = [
            "last_edited_by",
            "created_time",
            "last_edited_time",
            "created_by",
            "request_id",
        ]
        if parent_type == "block":
            self.logger.warning(
                "Skipping database with block type parent as "
                "appension is currently unsupported by Notion API"
            )
            child_database = {}
        else:
            database = self.get_database(child_notion_data["id"])
            child_database_data = {
                key: value
                for (key, value) in database.notion_data.items()
                if key not in bad_keys
            }
            child_database_data["parent"] = {
                "type": f"{parent_type}_id",
                f"{parent_type}_id": parent.notion_id,
            }
            child_database = self.create_notion_database(child_database_data)
            if database.children:
                notion_children = [child.notion_data for child in database.children]
                self.copy_notion_database_children(notion_children, child_database)
        return child_database

    def create_notion_comment(self, page_id, text_blocks_descriptors):
        data = {
            "rich_text": mock_rich_text_array(text_blocks_descriptors),
            "parent": {
                "type": "page_id",
                "page_id": page_id,
            },
        }
        return self._post_url(f"{self.base_url}comments", data)

    def create_notion_database(self, notion_data):
        return self._post_url(f"{self.base_url}databases", notion_data)

    def delete_notion_block(self, notion_block):
        return self._delete_url(f"{self.base_url}blocks/{notion_block['id']}")

    def class_is_in_use(self, class_object, cls):
        """
        Checks if the given class object has been instantiated
        with the currently favored class type for that class.
        """
        if class_object is None or type(class_object) is self.notion_classes[cls][-1]:
            return True
        return False

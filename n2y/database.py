from n2y.utils import fromisoformat, sanitize_filename


class Database:
    def __init__(self, client, notion_data):
        client.logger.debug("Instantiating database")
        self.client = client

        self.notion_data = notion_data
        self.notion_id = notion_data["id"]
        self.created_time = fromisoformat(notion_data["created_time"])
        self.created_by = client.wrap_notion_user(notion_data["created_by"])
        self.last_edited_time = fromisoformat(notion_data["last_edited_time"])
        self.last_edited_by = client.wrap_notion_user(notion_data["last_edited_by"])
        self.title = client.wrap_notion_rich_text_array(notion_data["title"])
        self.icon = self._init_icon(notion_data["icon"])
        self.cover = notion_data["cover"] and client.wrap_notion_file(
            notion_data["cover"]
        )
        self.archived = notion_data["archived"]
        self.schema = {
            k: client.wrap_notion_property(p)
            for k, p in notion_data["properties"].items()
        }
        self.notion_parent = notion_data["parent"]
        self.notion_url = notion_data["url"]
        self.archived = notion_data["archived"]

        self._children = None
        self._filtered_children = {}

    @property
    def filename(self):
        return sanitize_filename(self.title.to_plain_text())

    @property
    def children(self):
        if self._children is None:
            self._children = self.client.get_database_pages(self.notion_id)
        return self._children

    def children_filtered(self, filter, sort=None):
        if filter is not None:
            tupled_filter = self._tuplize(filter)
            tupled_sort = self._tuplize(sort)
            if tupled_filter not in self._filtered_children:
                self._filtered_children[tupled_filter] = {}
            if tupled_sort not in self._filtered_children[tupled_filter]:
                self._filtered_children[tupled_filter][tupled_sort] = (
                    self.client.get_database_pages(self.notion_id, filter, sort)
                )
            children = self._filtered_children[tupled_filter][tupled_sort]
        else:
            children = self.children
        return children

    def _tuplize(self, item):
        if callable(getattr(item, "items", None)):
            return tuple((key, self._tuplize(val)) for (key, val) in item.items())
        elif hasattr(item, "__iter__") and not isinstance(item, str):
            return tuple(self._tuplize(i) for i in item)
        else:
            return (item,)

    def _init_icon(self, icon_notion_data):
        """
        The icon property is unique in that it can be either an emoji or a file.
        """
        if icon_notion_data is None:
            return None
        elif icon_notion_data["type"] == "emoji":
            return self.client.wrap_notion_emoji(icon_notion_data)
        else:
            return self.client.wrap_notion_file(icon_notion_data)

    @property
    def parent(self):
        """
        The parent of a database can be a page, another database, a block, or
        it can be at the top level of workspace.
        """
        type = self.notion_parent["type"]
        if type == "workspace":
            return None

        if type == "page_id":
            return self.client.get_page(self.notion_parent["page_id"])

        if type == "database_id":
            return self.client.get_database(self.notion_parent["database_id"])

        if type == "block_id":
            return self.client.get_block(self.notion_parent["block_id"], page=None)

    def to_pandoc(self):
        return self.block.to_pandoc()

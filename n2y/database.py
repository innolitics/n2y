import logging

from n2y.utils import fromisoformat, sanitize_filename


logger = logging.getLogger(__name__)


class Database:
    def __init__(self, client, notion_data):
        logger.debug("Instantiating database")
        self.client = client

        self.notion_data = notion_data
        self.notion_id = notion_data['id']
        self.created_time = fromisoformat(notion_data['created_time'])
        self.created_by = client.wrap_notion_user(notion_data['created_by'])
        self.last_edited_time = fromisoformat(notion_data['last_edited_time'])
        self.last_edited_by = client.wrap_notion_user(notion_data['last_edited_by'])
        self.title = client.wrap_notion_rich_text_array(notion_data['title'])
        self.icon = notion_data['icon'] and client.wrap_notion_file(notion_data['icon'])
        self.cover = notion_data['cover'] and client.wrap_notion_file(notion_data['cover'])
        self.archived = notion_data['archived']
        self.schema = {
            k: client.wrap_notion_property(p)
            for k, p in notion_data['properties'].items()
        }
        self.notion_parent = notion_data['parent']
        self.notion_url = notion_data['url']
        self.archived = notion_data['archived']

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

    def get_children(self):
        self._children = self.client.get_database_pages(self.notion_id)

    def children_filtered(self, filter, sort=None):
        if not filter:
            return self.children
        else:
            tupled_filter = self._tuplize(filter)
            tupled_sort = self._tuplize(sort)
            if tupled_filter not in self._filtered_children:
                self._filtered_children[tupled_filter] = {}
            if tupled_sort not in self._filtered_children[tupled_filter]:
                self._filtered_children[tupled_filter][tupled_sort] = \
                    self.client.get_database_pages(self.notion_id, filter, sort)
            return self._filtered_children[tupled_filter][tupled_sort]

    def _tuplize(self, item):
        if callable(getattr(item, "items", None)):
            return tuple([(key, self._tuplize(val)) for (key, val) in item.items()])
        elif hasattr(item, '__iter__') and type(item) is not str:
            return tuple([self._tuplize(i) for i in item])
        else:
            return (item)

    @property
    def parent(self):
        if self.notion_parent["type"] == "workspace":
            return None
        else:
            return self.client.get_page(self.notion_parent["page_id"])

    def to_pandoc(self):
        return self.block.to_pandoc()

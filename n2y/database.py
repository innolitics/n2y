import logging

import yaml

from n2y.page import Page
from n2y.properties import RelationProperty
from n2y.utils import fromisoformat


logger = logging.getLogger(__name__)


class Database:
    def __init__(self, client, notion_data, parent=None):
        logger.debug("Instantiating page")
        self.client = client

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
        self.parent = parent
        self.url = notion_data['url']
        self.archived = notion_data['archived']

        self._children = None

    @property
    def children(self):
        if self._children is None:
            notion_pages = self.client.get_database_notion_pages(self.notion_id)
            self._children = [Page(self.client, np) for np in notion_pages]
        return self._children

    @property
    def related_database_ids(self):
        ids = []
        for prop in self.schema.values():
            if isinstance(prop, RelationProperty):
                ids.append(prop.database_id)
        return ids

    def to_pandoc(self):
        return self.block.to_pandoc()

    def to_yaml(self):
        result = []
        for page in self.children:
            content = page.content_to_markdown()
            properties = page.properties_to_values()
            # TODO: let the user set the name of the content key
            result.append({**properties, 'content': content})
        return yaml.dump(result, sort_keys=False)

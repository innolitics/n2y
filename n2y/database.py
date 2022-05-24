import logging

import yaml

from n2y.file import File
from n2y.page import Page
from n2y.rich_text import RichTextArray


logger = logging.getLogger(__name__)


class Database:
    def __init__(self, client, database, parent=None):
        logger.debug("Instantiating page")
        self.client = client

        self.notion_id = database['id']
        self.created_time = database['created_time']
        self.created_by = database['created_by']
        self.last_edited_time = database['last_edited_time']
        self.last_edited_by = database['last_edited_by']
        self.title = RichTextArray(database['title'])
        self.icon = database['icon'] and File(client, database['icon'])
        self.cover = database['cover'] and File(client, database['cover'])
        self.archived = database['archived']
        # self.schema = TODO: Grab property schema objects
        self.notion_parent = database['parent']
        self.parent = parent
        self.url = database['url']
        self.archived = database['archived']

        self._children = None

    @property
    def children(self):
        if self._children is None:
            notion_pages = self.client.get_database_notion_pages(self.notion_id)
            self._children = [Page(self.client, np) for np in notion_pages]
        return self._children

    def to_pandoc(self):
        return self.block.to_pandoc()

    def to_markdown(self):
        # TODO: copy over from main
        pass

    def to_yaml(self):
        result = []
        for page in self.children:
            content = page.content_to_markdown()
            result.append({**page.properties, 'content': content})
        return yaml.dump(result, sort_keys=False)

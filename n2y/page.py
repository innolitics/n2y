import logging

import yaml
import pandoc

from n2y.file import File
from n2y.property_values import flatten_property_values


logger = logging.getLogger(__name__)


class Page:
    def __init__(self, client, notion_page, parent=None):
        logger.debug("Instantiating page")
        self.client = client

        self.notion_id = notion_page['id']
        self.created_time = notion_page['created_time']
        self.created_by = notion_page['created_by']
        self.last_edited_time = notion_page['last_edited_time']
        self.last_edited_by = notion_page['last_edited_by']
        self.archived = notion_page['archived']
        self.icon = notion_page['icon'] and File(client, notion_page['icon'])
        self.cover = notion_page['cover'] and File(client, notion_page['cover'])
        self.archived = notion_page['archived']
        self.properties = flatten_property_values(notion_page['properties'])
        self.notion_parent = notion_page['parent']
        self.parent = parent
        self.url = notion_page['url']

        self._block = None
        self._children = None

    @property
    def block(self):
        if self._block is None:
            self._block = self.client.get_block(self.notion_id)
        return self._block

    @property
    def children(self):
        if self._children is None:
            self._children = True  # TODO: Implement this
            raise NotImplementedError()
            # recursively look through blocks for child_pages and child_databases,
            # creating them in order that they appear in the block heirarchy
        return self._children

    def to_pandoc(self):
        return self.block.to_pandoc()

    def content_to_markdown(self):
        pandoc_ast = self.to_pandoc()
        if pandoc_ast is not None:
            return pandoc.write(pandoc_ast, format='gfm+tex_math_dollars').replace('\r\n', '\n')
        else:
            return None

    def to_markdown(self):
        return '\n'.join([
            '---',
            yaml.dump(self.properties),
            '---',
            self.content_to_markdown() or '',
        ])

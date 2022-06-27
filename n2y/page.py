import logging

import yaml

from n2y.utils import pandoc_ast_to_markdown, fromisoformat, sanitize_filename
from n2y.property_values import TitlePropertyValue


logger = logging.getLogger(__name__)


class Page:
    def __init__(self, client, notion_data):
        logger.debug("Instantiating page")
        self.client = client

        self.notion_id = notion_data['id']
        self.created_time = fromisoformat(notion_data['created_time'])
        self.created_by = client.wrap_notion_user(notion_data['created_by'])
        self.last_edited_time = fromisoformat(notion_data['last_edited_time'])
        self.last_edited_by = client.wrap_notion_user(notion_data['last_edited_by'])
        self.archived = notion_data['archived']
        self.icon = notion_data['icon'] and client.wrap_notion_file(notion_data['icon'])
        self.cover = notion_data['cover'] and client.wrap_notion_file(notion_data['cover'])
        self.archived = notion_data['archived']
        self.properties = {
            k: client.wrap_notion_property_value(npv)
            for k, npv in notion_data['properties'].items()
        }
        self.notion_parent = notion_data['parent']
        self.notion_url = notion_data['url']

        self._block = None
        self._children = None

    @property
    def title(self):
        for property_value in self.properties.values():
            # Notion ensure's there is always exactly one title property
            if isinstance(property_value, TitlePropertyValue):
                return property_value.rich_text

    @property
    def filename(self):
        # TODO: switch to using the database's natural keys as the file names
        return sanitize_filename(self.title.to_plain_text())

    @property
    def block(self):
        if self._block is None:
            self._block = self.client.get_block(self.notion_id, page=self)
        return self._block

    @property
    def children(self):
        if self._children is None:
            self._children = True  # TODO: Implement this
            raise NotImplementedError()
            # recursively look through blocks for child_pages and child_databases,
            # creating them in order that they appear in the block heirarchy
        return self._children

    @property
    def parent(self):
        parent_type = self.notion_parent["type"]
        if parent_type == "workspace":
            return None
        elif parent_type == "page_id":
            return self.client.get_page(self.notion_parent["page_id"])
        else:
            assert parent_type == "database_id"
            return self.client.get_database(self.notion_parent["database_id"])

    def to_pandoc(self):
        return self.block.to_pandoc()

    def content_to_markdown(self):
        pandoc_ast = self.to_pandoc()
        if pandoc_ast is not None:
            return pandoc_ast_to_markdown(pandoc_ast)
        else:
            return None

    def properties_to_values(self):
        return {k: v.to_value() for k, v in self.properties.items()}

    def to_markdown(self):
        return '\n'.join([
            '---',
            yaml.dump(self.properties_to_values()) + '---',
            self.content_to_markdown() or '',
        ])

from n2y.blocks import ChildDatabaseBlock, ChildPageBlock, TableOfContentsBlock
from n2y.property_values import TitlePropertyValue
from n2y.utils import fromisoformat


class Page:
    def __init__(self, client, notion_data):
        client.logger.debug("Instantiating page")
        self.notion_parent = notion_data["parent"]
        self.archived = notion_data["archived"]
        self.notion_url = notion_data["url"]
        self.notion_id = notion_data["id"]
        self.notion_data = notion_data
        self.plugin_data = {}
        self._children = None
        self.client = client
        self._block = None

        self.created_time = fromisoformat(notion_data["created_time"])
        self.last_edited_time = fromisoformat(notion_data["last_edited_time"])
        self.created_by = client.wrap_notion_user(notion_data["created_by"])
        self.last_edited_by = client.wrap_notion_user(notion_data["last_edited_by"])
        self.icon = self._init_icon(notion_data["icon"])
        self.cover = notion_data["cover"] and client.wrap_notion_file(
            notion_data["cover"]
        )
        self.properties = {
            k: client.wrap_notion_property_value(npv, self)
            for k, npv in notion_data["properties"].items()
        }

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
    def title(self):
        for property_value in self.properties.values():
            # Notion ensures there is always exactly one title property
            if isinstance(property_value, TitlePropertyValue):
                return property_value.rich_text

    @property
    def block(self):
        if self._block is None:
            self._block = self.client.get_block(self.notion_id, page=self)
        return self._block

    @property
    def children(self):
        """
        Get a list of child pages and databases.
        """
        if self._children is None:
            self._children = []
            for block in self.block.children:
                self._append_children(block)
        return self._children

    def get_children(self):
        self.block.get_children()
        self._children = []
        for block in self.block.children:
            self._append_children(block)

    def _append_children(self, block):
        if isinstance(block, ChildPageBlock):
            page = self.client.get_page(block.notion_id)
            self._children.append(page)
        elif isinstance(block, ChildDatabaseBlock):
            database = self.client.get_database(block.notion_id)
            self._children.append(database)
        elif block.children is not None:
            # Recursively look for child pages and databases in the hierarchy
            for child_block in block.children:
                self._append_children(child_block)

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

    def generate_toc(self, ast):
        """
        Generate a table of contents for the page.
        """
        toc_indecies = []

        def is_toc(i, block):
            if type(block) is TableOfContentsBlock:
                toc_indecies.append(i)
                return True
            return False

        if any(is_toc(*t) for t in enumerate(self.block.children)):
            child_ast = ast[1]
            for i in toc_indecies:
                self.block.children[i].render_toc(child_ast)
            ast = self.block.to_pandoc()
        return ast

    def to_pandoc(self, ignore_toc=False):
        ast = self.block.to_pandoc()
        return ast if ignore_toc else self.generate_toc(ast)

    def properties_to_values(self, pandoc_format=None, pandoc_options=None):
        return {
            k: v.to_value(pandoc_format, pandoc_options)
            for k, v in self.properties.items()
        }

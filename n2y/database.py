import logging

import yaml

from n2y.property_values import RelationPropertyValue
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
            self._children = self.client.get_database_pages(self.notion_id, self)
        return self._children

    @property
    def related_database_ids(self):
        """
        This method is much more complicated than it should be due to
        limitations of the Notion API.

        First, one would expect that the RelationProperty objects would be
        present in the databases's properties features, however they do not
        show up _unless_ the relationship is back to the same database.

        Secondly, one would expect that the page property endpoint
        (https://developers.notion.com/reference/retrieve-a-page-property)
        would enable one to retrieve the related database id from the property
        directly, however, the database id doesn't appear to be returned there
        either.

        As a last result, this method will first get the first page in a
        database (raising an error if there are no pages). Then, it will loop
        through the properties of the page to find any relationship properties.
        Then, it will loop through all pages in the database to find one that
        actually has a value of a page in the related database. Finally, we
        retrieve the related page and get the database ID from the parent.
        """
        if len(self.children) == 0:
            raise ValueError("Unable to identify relationships for an empty database")
        first_page = self.children[0]
        ids = []
        for prop_name, prop in first_page.properties.items():
            if isinstance(prop, RelationPropertyValue):
                related_page_id = None
                for page in self.children:
                    related_page_ids = page.properties[prop_name].ids
                    if len(related_page_ids) > 0:
                        related_page_id = related_page_ids[0]
                        break
                if related_page_id is None:
                    raise ValueError(
                        'Unable to identify database for relationship "{prop_name}" '
                        'because there are no values in the entire database'
                    )
                related_page = self.client.get_page(related_page_id)
                assert related_page.notion_parent["type"] == "database_id"
                ids.append(related_page.notion_parent["database_id"])
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

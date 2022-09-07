import logging

from n2y.blocks import LinkToPageBlock

# TODO: The work of this function is a (predictably recursive)
# retrieval of the content of the page to which the link points.
# The theory, therefore, is straightforward: return a pandoc representation of the 
# linked page.  For that, it should suffice to 

# TODO: QUESTION Wwhat pandoc types do I need?
from pandoc.types import Header, Link

logger = logging.getLogger(__name__)

# Do I want to instantiate Client for the linked page?  I think not.
# QUESTION I am unsure of the best way to instantiate the linked page. 

class LinkToPage(LinkToPageBlock):
    """
    Replace page link with the content of the linked-to page.

    """
    def __init__(self, client, notion_data, page, get_children=False):

        self.notion_id = notion_data['id'] # Unused
        self.notion_type = notion_data['type'] # Unused
        self.notion_data = notion_data[notion_data['page_id']]  # The id of the linked-to page

        # Create Client object for linked to page.
        self.client = notion_data

    def to_pandoc(self):
        assert self.notion_data is not None

        # QUESTION As link_to_page can reference either a page or a database, although the assignment was
        # for a "page", shouldn't we be able to accommodate a datbase as well? 

        # TODO. Should be a simple operation here to run the whole of the linked-to
        # page through n2y.  Then nothing here special needs to be done. 
        return self.process_subpage(self)


    def process_subpage(self):

            # Handle the case where a link to a page is outside of the 
            # authorized Notion tree.

            # Could use notion.py Client class on the id of the linked page, 
            # and catch any access error.

            # For example,  get_notion_block() method of Client will return
            # an access denied error.

        try:
           self.client.get_page(self.linked_page) 
           # Although out of the scope of this assignment, get_page_or_database() could be used in place of get_page, to cover the linked database case. 

        # TODO: At this point, only need to return pandoc of linked_page.  QUESTION What is the 
        # most compact way to convert the notion page to pandoc here?

           return None
 
          
        except PermissionError:
            msg = 'Permission denied when attempting to access linked page having id [%s]'
            logger.warning(msg, self.notion_data)


notion_classes = {
    "blocks": {
        "link_to_page": LinkToPage,
    }
}

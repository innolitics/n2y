import logging

from n2y.utils import fromisoformat

logger = logging.getLogger(__name__)


class Comment:
    """
    See https://developers.notion.com/reference/comment-object
    """

    def __init__(self, client, notion_data):
        self.notion_id = notion_data["id"]
        self.notion_parent = notion_data['parent']
        self.discussion_id = notion_data["discussion_id"]
        self.created_time = fromisoformat(notion_data['created_time'])
        self.last_edited_time = fromisoformat(notion_data['last_edited_time'])
        self.created_by = client.wrap_notion_user(notion_data['created_by'])
        self.rich_text = client.wrap_notion_rich_text_array(notion_data["rich_text"], self)

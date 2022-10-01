import logging


logger = logging.getLogger(__name__)


class Emoji:
    """
    See https://developers.notion.com/reference/emoji-object
    """

    def __init__(self, client, notion_data):
        self.client = client
        self.emoji = notion_data['emoji']

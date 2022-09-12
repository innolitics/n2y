from pandoc.types import Str
from n2y.blocks import RowBlock

from n2y.utils import process_notion_date, processed_date_to_plain_text


class Mention:
    def __init__(self, client, notion_data, plain_text, block=None):
        self.client = client
        self.block = block
        self.plain_text = plain_text
        self.notion_type = notion_data["type"]


class UserMention(Mention):
    def __init__(self, client, notion_data, plain_text, block=None):
        super().__init__(client, notion_data, plain_text, block)
        self.user = client.wrap_notion_user(notion_data["user"])

    def to_pandoc(self):
        return [Str(self.user.name)] if self.user.name else []


class PageMention(Mention):
    def __init__(self, client, notion_data, plain_text, block=None):
        # workaround for a bug in the Notion API wheren the plain_text is
        # untitled inside simple tables
        if plain_text == "Untitled" and isinstance(block, RowBlock):
            page = client.get_page(notion_data["page"]["id"])
            if page is not None:
                plain_text = page.title.to_plain_text()

        super().__init__(client, notion_data, plain_text, block)
        self.notion_page_id = notion_data["page"]["id"]

    def to_pandoc(self):
        # TODO: if the page is being exported too, then make this a relative
        # URL to that page
        return [Str(self.plain_text)]


class DatabaseMention(Mention):
    def __init__(self, client, notion_data, plain_text, block=None):
        super().__init__(client, notion_data, plain_text, block)
        self.notion_database_id = notion_data["database"]["id"]

    def to_pandoc(self):
        return [Str(self.plain_text)]


class DateMention(Mention):
    def __init__(self, client, notion_data, plain_text, block=None):
        super().__init__(client, notion_data, plain_text, block)
        self.processed_date = process_notion_date(notion_data["date"])

    def to_pandoc(self):
        # TODO: Consider just using plain_text here
        plain_text_date = processed_date_to_plain_text(self.processed_date)
        return [Str(plain_text_date)]


class LinkPreviewMention(Mention):
    def __init__(self, client, notion_data, plain_text, block=None):
        super().__init__(client, notion_data, plain_text, block)
        self.url = notion_data["link_preview"]["url"]

    def to_pandoc(self):
        return [Str(self.url)]


# TODO: handle template button date and user mentions

DEFAULT_MENTIONS = {
    "user": UserMention,
    "page": PageMention,
    "database": DatabaseMention,
    "date": DateMention,
    "link_preview": LinkPreviewMention,
}

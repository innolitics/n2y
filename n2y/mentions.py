from pandoc.types import Str

from n2y.utils import process_notion_date, processed_date_to_plain_text


class Mention:
    def __init__(self, client, notion_data):
        self.client = client
        self.notion_type = notion_data["type"]


class UserMention(Mention):
    def __init__(self, client, notion_data):
        super().__init__(client, notion_data)
        self.user = client.wrap_notion_user(notion_data["user"])

    def to_pandoc(self):
        return [Str(self.user.name)]


class PageMention(Mention):
    def __init__(self, client, notion_data):
        super().__init__(client, notion_data)
        self.page = client.get_page(notion_data["page"]["id"])

    def to_pandoc(self):
        if self.page is not None:
            # TODO: if the page is being exported too, then make this a relative
            # URL to that page
            return self.page.title.to_pandoc()
        else:
            return [Str("Untitled")]


class DatabaseMention(Mention):
    def __init__(self, client, notion_data):
        super().__init__(client, notion_data)
        self.database = client.get_database(notion_data["database"]["id"])

    def to_pandoc(self):
        if self.database is not None:
            return self.database.title.to_pandoc()
        else:
            return [Str("Untitled")]


class DateMention(Mention):
    def __init__(self, client, notion_data):
        super().__init__(client, notion_data)
        self.processed_date = process_notion_date(notion_data["date"])

    def to_pandoc(self):
        plain_text_date = processed_date_to_plain_text(self.processed_date)
        return [Str(plain_text_date)]


class LinkPreviewMention(Mention):
    def __init__(self, client, notion_data):
        super().__init__(client, notion_data)
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

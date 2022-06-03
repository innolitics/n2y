from pandoc.types import Str


class Mention:
    def __init__(self, client, notion_data):
        self.client = client
        self.notion_type = notion_data["type"]


class UserMention(Mention):
    def __init__(self, client, notion_data):
        super().__init__(client, notion_data)
        self.user = client.wrap_notion_user(notion_data["user"])

    def to_pandoc(self):
        return [Str(self.user["name"])]


class PageMention(Mention):
    def __init__(self, client, notion_data):
        super().__init__(client, notion_data)
        self.page_id = notion_data["id"]

    def to_pandoc(self):
        # TODO: at least replace with the page title
        # TODO: incorporate when implementing https://github.com/innolitics/n2y/issues/24
        return [Str(f'Link to page "{self.page_id}"')]


class DatabaseMention(Mention):
    def __init__(self, client, notion_data):
        super().__init__(client, notion_data)
        self.database_id = notion_data["id"]

    def to_pandoc(self):
        # TODO: at least replace with the database title
        # TODO: incorporate when implementing https://github.com/innolitics/n2y/issues/24
        return [Str(f'Link to database "{self.database_id}"')]


class DateMention(Mention):
    def __init__(self, client, notion_data):
        super().__init__(client, notion_data)
        self.date = client.wrap_notion_property_value(notion_data["date"])

    def to_pandoc(self):
        return [Str(self.date.to_plain_text())]


class LinkPreviewMention(Mention):
    def __init__(self, client, notion_data):
        super().__init__(client, notion_data)
        self.url = notion_data["url"]

    def to_pandoc(self):
        return [Str(self.href)]


# TODO: handle template button date and user mentions

DEFAULT_MENTIONS = {
    "user": UserMention,
    "page": PageMention,
    "database": DatabaseMention,
    "date": DateMention,
    "link_preview": LinkPreviewMention,
}

class User:
    def __init__(self, client, notion_data):
        self.client = client
        self.notion_data = notion_data
        self.notion_id = notion_data["id"]
        self.notion_type = notion_data.get("type", None)
        self.name = notion_data.get("name", None)
        self.avatar_url = notion_data.get("avatar_url", None)
        if self.notion_type == "person" and "email" in notion_data["person"]:
            self.email = notion_data["person"]["email"]
        else:
            self.email = None
        # TODO: handle bot users

    def to_value(self):
        # TODO: consider how to handle people with the same name. E.g., maybe we
        # should at least show a warning
        return self.name or ""

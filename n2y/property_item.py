class PropertyItem:
    def __init__(self, client, notion_data):
        if notion_data["object"] != "list":
            self.property_value = client.wrap_notion_property_value(notion_data)
        else:
            self.property_value = client.instantiate_class(
                "property_values",
                notion_data["property_item"]["type"],
                client,
                notion_data,
            )

    def to_value(self):
        return self.property_value.to_value()

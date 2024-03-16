class File:
    """
    See https://developers.notion.com/reference/file-object
    """

    def __init__(self, client, notion_data):
        self.client = client
        if notion_data["type"] == "file":
            client.logger.debug('Instantiating file "%s"', notion_data["file"]["url"])
            self.type = "file"
            self.url = notion_data["file"]["url"]
            self.expiry_time = notion_data["file"]["expiry_time"]
        elif notion_data["type"] == "external":
            client.logger.debug(
                'Instantiating external file "%s"', notion_data["external"]["url"]
            )
            self.type = "external"
            self.url = notion_data["external"]["url"]
        else:
            file_type = notion_data["type"]
            raise ValueError(f'Unknown file type "{file_type}"')

    def to_value(self):
        return self.url

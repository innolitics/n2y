from os import makedirs, path
from urllib.parse import urljoin, urlparse

from n2y.file import File as OldFile
from n2y.logger import logger
from n2y.utils import strip_hyphens


class File(OldFile):
    def __init__(self, client, notion_data):
        self.client = client
        self.name = notion_data["name"]
        if notion_data["type"] == "file":
            logger.debug('Instantiating file "%s"', notion_data["file"]["url"])
            self.type = "file"
            self.url = self.download_file(notion_data["file"]["url"])
        elif notion_data["type"] == "external":
            logger.debug(
                'Instantiating external file "%s"', notion_data["external"]["url"]
            )
            self.type = "external"
            self.url = notion_data["external"]["url"]
        else:
            file_type = notion_data["type"]
            raise ValueError(f'Unknown file type "{file_type}"')

    def download_file(self, url):
        """
        Download a file from a given URL into the MEDIA_ROOT.

        Preserve the file extension from the URL, but use the
        id of the block followed by an md5 hash.
        """
        content = self.client._get_url(url, stream=True)
        return self.save_file(content)

    def save_file(self, content):
        full_filepath = path.join(self.client.media_root, self.name)
        makedirs(self.client.media_root, exist_ok=True)
        with open(full_filepath, "wb") as temp_file:
            temp_file.write(content)
        return urljoin(self.client.media_url, self.name)


notion_classes = {
    "file": File,
}

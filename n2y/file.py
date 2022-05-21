import logging

from n2y.notion import Client


logger = logging.getLogger(__name__)


class File:
    """
    See https://developers.notion.com/reference/file-object
    """

    def __init__(self, client: Client, file):
        logger.debug('Instantiating file "%s"', file['file']['url'])
        self.client = client
        if file['type'] == "file":
            self.type = "file"
            self.url = file['file']['url']
            self.expiry_time = file['file']['expiry_time']
        elif file['type'] == "external":
            self.type = "external"
            self.url = file['external']['url']

    def download(self):
        return self.client.download_file(self.url)

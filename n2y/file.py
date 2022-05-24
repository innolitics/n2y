import logging


logger = logging.getLogger(__name__)


class File:
    """
    See https://developers.notion.com/reference/file-object
    """

    def __init__(self, client, file):
        self.client = client
        if file['type'] == "file":
            logger.debug('Instantiating file "%s"', file['file']['url'])
            self.type = "file"
            self.url = file['file']['url']
            self.expiry_time = file['file']['expiry_time']
        elif file['type'] == "external":
            logger.debug('Instantiating external file "%s"', file['external']['url'])
            self.type = "external"
            self.url = file['external']['url']
        else:
            file_type = file['type']
            raise ValueError(f'Unknown file type "{file_type}"')

    def download(self):
        return self.client.download_file(self.url)

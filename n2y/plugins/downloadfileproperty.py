import hashlib
from os import makedirs, path
from urllib.parse import urlparse

from n2y.property_values import FilesPropertyValue
from n2y.utils import slugify


class DownloadFilePropertyValue(FilesPropertyValue):
    def to_value(self, _, __):
        url_list = []
        for file in self.files:
            file_content = self.client._get_url(file.url, stream=True)
            url_path = path.basename(urlparse(file.url).path)
            _, extension = path.splitext(url_path)
            file_hash = hashlib.sha256(file_content).hexdigest()[:10]
            page_title_slug = slugify(self.page.title.to_plain_text())
            file_name = f"{page_title_slug}-{file_hash}{extension}"
            full_filepath = path.join(self.client.media_root, file_name)
            makedirs(self.client.media_root, exist_ok=True)
            with open(full_filepath, "wb") as file:
                file.write(file_content)
            url_list.append(path.join(self.client.media_url, file_name))
        return url_list


notion_classes = {"property_values": {"files": DownloadFilePropertyValue}}

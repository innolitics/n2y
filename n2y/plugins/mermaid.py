import logging
import os
import subprocess
import tempfile

from pandoc.types import Para, Image

from n2y.blocks import FencedCodeBlock
from n2y.errors import UseNextClass


logger = logging.getLogger(__name__)


class MermaidFencedCodeBlock(FencedCodeBlock):
    """
    Adds support for generating mermaid diagrams from codeblocks with the
    "mermaid" language, as supported in the Notion UI.

    This plugin assumes that the `mmdc` mermaid commandline tool is available,
    and will throw an exception if it is not.

    If there are errors with the mermaid syntax, it is treated as a normal
    codeblock and the warning is logged.
    """

    def __init__(self, client, page, notion_data, get_children=True):
        super().__init__(client, page, notion_data, get_children)
        if self.language != "mermaid":
            raise UseNextClass()

    def to_pandoc(self):
        temp_fd, temp_filepath = tempfile.mkstemp(suffix=".png")
        os.close(temp_fd)
        try:
            diagram_as_bytes = self.rich_text.to_plain_text().encode()
            subprocess.run([
                'mmdc',
                '-o', temp_filepath,
            ], capture_output=True, input=diagram_as_bytes, check=True)
            with open(temp_filepath, 'rb') as temp_file:
                content_iterator = iter(lambda: temp_file.read(4096), b'')
                url = self.client.save_file(content_iterator, self.page, '.png')
            return Para([Image(('', [], []), self.caption.to_pandoc(), (url, ''))])
        except subprocess.CalledProcessError as exc:
            # as of now, mmdc does not ever return a non-zero error code, so
            # this won't ever be hit
            msg = (
                "Unable to convert mermaid diagram (%s) into an image. "
                "The mermaid-cli returned error code %d and printed: %s"
            )
            logger.error(msg, self.notion_url, exc.returncode, exc.stderr)
        except subprocess.SubprocessError:
            msg = "Unable to convert mermaid diagram (%s) into an image"
            logger.exception(msg, self.notion_url)
        except FileNotFoundError:
            msg = (
                "Unable to find the mermaid-cli executable, `mmdc`, on the PATH. "
                "See here: https://github.com/mermaid-js/mermaid-cli "
                "Mermaid diagram (%s) in code blocks will not be converted to images."
            )
            logger.error(msg, self.notion_url)
        return super().to_pandoc()


notion_classes = {
    "blocks": {
        "code": MermaidFencedCodeBlock,
    }
}

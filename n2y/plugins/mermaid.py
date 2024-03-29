import json
import os
import subprocess
import tempfile
from pathlib import Path

from pandoc.types import Image, Para

from n2y.blocks import FencedCodeBlock
from n2y.errors import UseNextClass

mermaid_config = {"flowchart": {"useMaxWidth": False}}

puppeteer_config = {
    "headless": True,
    "args": [
        "--no-sandbox",
        "--disable-setuid-sandbox",
    ],
}


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
        # TODO: Clean up by extracting all this temp code out
        temp_fd, temp_filepath = tempfile.mkstemp(suffix=".png")
        os.close(temp_fd)
        temp_config_mermaid_fd, temp_config_mermaid_filepath = tempfile.mkstemp(
            suffix=".json"
        )
        os.write(temp_config_mermaid_fd, json.dumps(mermaid_config).encode("utf-8"))
        os.close(temp_config_mermaid_fd)
        temp_config_puppeteer_fd, temp_config_puppeteer_filepath = tempfile.mkstemp(
            suffix=".json"
        )
        os.write(temp_config_puppeteer_fd, json.dumps(puppeteer_config).encode("utf-8"))
        os.close(temp_config_puppeteer_fd)
        try:
            diagram_as_text = self.rich_text.to_plain_text()
            diagram_as_bytes = diagram_as_text.encode()
            subprocess.run(
                [
                    "mmdc",
                    "--configFile",
                    temp_config_mermaid_filepath,
                    "--puppeteerConfigFile",
                    temp_config_puppeteer_filepath,
                    "-o",
                    temp_filepath,
                ],
                capture_output=True,
                input=diagram_as_bytes,
                check=True,
            )
            with open(temp_filepath, "rb") as temp_file:
                content = temp_file.read()
                root = Path(__file__).resolve().parent.parent
                with open(root / "data" / "mermaid_err.png", "rb") as err_img:
                    if content == err_img.read():
                        raise NotImplementedError("Syntax Error In Graph")
                url = self.client.save_file(content, self.page, ".png", self.notion_id)
                caption = []
                fig_flag = ""
                if self.caption:
                    fig_flag = "fig:"
                    caption = self.caption.to_pandoc()
            return Para([Image(("", [], []), caption, (url, fig_flag))])
        except subprocess.CalledProcessError as exc:
            # as of now, mmdc does not ever return a non-zero error code, so
            # this won't ever be hit
            msg = (
                "Unable to convert mermaid diagram (%s) into an image. "
                "The mermaid-cli returned error code %d and printed: %s"
            )
            self.client.logger.error(msg, self.notion_url, exc.returncode, exc.stderr)
        except subprocess.SubprocessError:
            msg = "Unable to convert mermaid diagram (%s) into an image"
            self.client.logger.exception(msg, self.notion_url)
        except NotImplementedError:
            msg = (
                "Unable to convert mermaid diagram (%s) into"
                " an image due to a syntax error in the graph"
            )
            self.client.logger.exception(msg, self.notion_url)
        except FileNotFoundError:
            msg = (
                "Unable to find the mermaid-cli executable, `mmdc`, on the PATH. "
                "See here: https://github.com/mermaid-js/mermaid-cli "
                "Mermaid diagram (%s) in code blocks will not be converted to images."
            )
            self.client.logger.error(msg, self.notion_url)
        return super().to_pandoc()


notion_classes = {
    "blocks": {
        "code": MermaidFencedCodeBlock,
    }
}

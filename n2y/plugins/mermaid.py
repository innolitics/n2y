import json
import os
import subprocess
import tempfile
from pathlib import Path

from pandoc.types import Image, Para

from n2y.blocks import FencedCodeBlock
from n2y.errors import UseNextClass


mermaid_config = {
    "flowchart": {"useMaxWidth": True},   # Forces diagrams to use available width
    "theme": "default",
    "themeVariables": {
        "fontSize": "30px",               # increases default font size for readability
        "lineColor": "#000000",         # effects color of connecting lines in diagrams
        "borderColor": "#000000",       # black border color for nodes to provide clear contrast
        "textColor": "#000000",         # sets text color globally to black for better readability
        "primaryColor": "#ffffff"       # fill background color in nodes
    }
}


puppeteer_config = {
    "headless": True,
    "args": [
        "--no-sandbox",
        "--disable-setuid-sandbox",
        "--force-device-scale-factor=6.0"  # Defines pixel density for browser rendering
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

    def _create_temp_json(self, config_dict):
        fd, filepath = tempfile.mkstemp(suffix=".json")
        os.write(fd, json.dumps(config_dict).encode("utf-8"))
        os.close(fd)
        return filepath

    def _create_temp_png(self):
        fd, filepath = tempfile.mkstemp(suffix=".png")
        os.close(fd)
        return filepath

    def to_pandoc(self):
        mermaid_config_path = self._create_temp_json(mermaid_config)
        puppeteer_config_path = self._create_temp_json(puppeteer_config)
        temp_png_path = self._create_temp_png()
        try:
            diagram_as_text = self.rich_text.to_plain_text()
            diagram_as_bytes = diagram_as_text.encode()
            subprocess.run(
                [
                    "mmdc",
                    "--configFile",
                    mermaid_config_path,
                    "--puppeteerConfigFile",
                    puppeteer_config_path,
                    "-o",
                    temp_png_path,
                    "--backgroundColor", "white",
                    "--scale", "3",
                ],
                capture_output=True,
                input=diagram_as_bytes,
                check=True,
            )
            with open(temp_png_path, "rb") as temp_file:
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
            return Para([Image(("", [], [("width", "100%")]), caption, (url, fig_flag))])
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
        finally:
            for path in [mermaid_config_path, puppeteer_config_path, temp_png_path]:
                try:
                    os.remove(path)
                except Exception:
                    pass
        return super().to_pandoc()


notion_classes = {
    "blocks": {
        "code": MermaidFencedCodeBlock,
    }
}

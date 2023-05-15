import pytest

from pathlib import Path

import yaml

try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader

import n2y
from n2y.main import main


def test_ordered_numerals(access_token, monkeypatch, request, tmp_path):
    """
    Relies on https://www.notion.so/Alternative-list-bullets-368426fe6f4d410a8775df57a8c0782c
    """
    object_id = "368426fe6f4d410a8775df57a8c0782c"

    config = {
        "exports": [
            {
                "id": object_id,
                "node_type": "page",
                "output": f"{request.node.name}-output",
                "pandoc_format": "plain"
            }
        ]
    }
    with monkeypatch.context() as m:
        m.chdir(tmp_path)
        config_path = Path("{}-config.yaml".format(request.node.name))
        with config_path.open("w") as fo:
            yaml.dump(config, fo)
        status = main([str(config_path)], access_token)
    assert status == 0, f"Status {status}"
    output_path = tmp_path / f"{request.node.name.replace('/', '-')}-output"
    content = output_path.read_text()
    assert """\
Nested list eventually reaches Roman Numerals

1.  Large digits
    a.  Small alphabetic
        i.  these
        ii. are
        iii. roman
        iv. numerals
    b.  Back to alphabetic
2.  Back to large digits
""" in content, "Failed to render implied Roman Numerals"
    assert """\
Explicitly set Roman Numerals

i.  these
ii. are
iii. roman
iv. numerals
""" in content, "Failed to render explicitly formatted Roman Numerals"

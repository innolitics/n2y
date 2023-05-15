import pytest

import difflib
import os
from pathlib import Path

import yaml
try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader

import n2y
from n2y.main import main

NOTION_ACCESS_TOKEN = os.getenv("NOTION_ACCESS_TOKEN") or 'secret_lylx4iL5awveY3re6opuvSQqM6sMRu572TowhfzPy5r'


@pytest.mark.skip("Choice of Markdown dialect will determine whether header-free simple tables render this way")
def test_simple_table(monkeypatch, request, tmp_path):
    """
    Simply show what flattened Markdown content is expected if the input contains tables without headers.

    Relies on https://www.notion.so/Simple-Tables-9b1dd705f61647b6a10032ec7671402f?pvs=4
    """
    object_id = "9b1dd705f61647b6a10032ec7671402f"

    config = {
        "exports": [
            {
                "id": object_id,
                "node_type": "page",
                "output": f"{request.node.name}-output",
                "pandoc_format": "gfm",
            }
        ]
    }
    with monkeypatch.context() as m:
        m.chdir(tmp_path)
        config_path = Path("{}-config.yaml".format(request.node.name))
        with config_path.open("w") as fo:
            yaml.dump(config, fo)
        status = main([str(config_path)], NOTION_ACCESS_TOKEN)
    assert status == 0, f"Status {status}"
    output_path = tmp_path / f"{request.node.name}-output"
    content = output_path.read_text()
    diff = list(difflib.context_diff("""\
---
notion_id: 9b1dd705-f616-47b6-a100-32ec7671402f
notion_url: https://www.notion.so/Simple-Tables-9b1dd705f61647b6a10032ec7671402f
title: Simple Tables
---
Some text

| This | has     |
| no   | headers |

More text

|        | header | row     |
|--------|--------|---------|
| header | This   | has     |
| column | both   | headers |
|        |        |         |
| and    | an     | empty   |

Yakkity yakkity yakkity yak

| header | Fiddle |
| column | Faddle |

| header | row    |
|--------|--------|
| Nutter | Butter |
""".splitlines(keepends=True), content.splitlines(keepends=True)))
    assert not diff, f"Markdown produced:\n{''.join(diff)}"


import pytest

from pathlib import Path

import yaml
try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader

import n2y
from n2y.main import main


def test_simple_table(access_token, monkeypatch, request, tmp_path):
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
        status = main([str(config_path)], access_token)
    assert status == 0, f"Status {status}"
    output_path = tmp_path / f"{request.node.name}-output"
    content = output_path.read_text()
    assert """\
Some text

| column-1 | column-2 |
|----------|----------|
| This     | has      |
| no       | headers  |

""" in content
    assert """\
More text

|        | header | row     |
|--------|--------|---------|
| header | This   | has     |
| column | both   | headers |
|        |        |         |
| and    | an     | empty   |
""" in content
    assert """\
Yakkity yakkity yakkity yak

| column-1 | column-2 |
|----------|----------|
| header   | Fiddle   |
| column   | Faddle   |

""" in content
    assert """\
| header | row    |
|--------|--------|
| Nutter | Butter |
""" in content

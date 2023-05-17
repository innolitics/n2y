import pytest  # noqa: E401

import logging
from pathlib import Path
import sys

import yaml

from n2y.main import main


def test_simple_table(caplog, monkeypatch, request, tmp_path,
                      valid_access_token):
    """
    Simply show what flattened Markdown content is expected if the input
    contains tables without headers.

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
        m.setattr(sys, "argv", ["n2y", str(config_path)])
        status = main()
        captured_messages = [r.message for r in caplog.records
                             if r.levelno >= logging.WARNING]
    assert status == 0, f"Status {status}"
    output_path = tmp_path / f"{request.node.name}-output"
    content = output_path.read_text()

    n_expected_table_warnings = 0
    if """\
Some text

|      |         |
|------|---------|
| This | has     |
| no   | headers |
""" in content:
        n_expected_table_warnings += 1
    assert """\
More text

|        | header | row     |
|--------|--------|---------|
| header | This   | has     |
| column | both   | headers |
|        |        |         |
| and    | an     | empty   |
""" in content
    if """\
Yakkity yakkity yakkity yak

|        |        |
|--------|--------|
| header | Fiddle |
| column | Faddle |
""" in content:
        n_expected_table_warnings += 1
    assert """\
| header | row    |
|--------|--------|
| Nutter | Butter |
"""
    if n_expected_table_warnings > 0:
        assert f"{n_expected_table_warnings} tables will present empty " \
               "headers to maintain Markdown spec" in captured_messages

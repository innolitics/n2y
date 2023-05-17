"""
Move data from Notion into YAML/markdown
"""

import os
import sys
import logging
import argparse
from pathlib import Path
import pkg_resources
import yaml

from n2y import notion
from n2y.config import load_config, merge_default_config
from n2y.utils import share_link_from_id
from n2y.export import export_page, database_to_yaml, database_to_markdown_files

logger = None


def _parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("config", help="The path to the config file",
                        type=Path)
    parser.add_argument(
        "--log-level", default="INFO",
        help="Level to set the root logging module to",
        type=lambda text: text.upper(),
    )
    parser.add_argument(
        "-v", "--verbose", action="store_const",
        dest="log_level", const="DEBUG",
        help="Set the log level to DEBUG",
    )
    parser.add_argument(
        "--version", action="version",
        version=pkg_resources.require("n2y")[0].version,
    )
    parser.set_defaults(access_token=os.getenv("NOTION_ACCESS_TOKEN"),
                        n2y_cache=os.getenv("N2Y_CACHE"))
    return parser.parse_args(argv)


def main():
    args = _parse_args()
    stdout_handler = logging.StreamHandler(stream=sys.stdout)
    logging.basicConfig(level=args.log_level, handlers=[stdout_handler])
    global logger
    logger = logging.getLogger(__name__)

    access_token = args.access_token
    n2y_cache = args.n2y_cache

    if n2y_cache is not None:
        try:
            import requests_cache
            requests_cache.install_cache(n2y_cache, backend='sqlite', expire_after=-1)
            logger.info("Using cache at %s", n2y_cache)
        except ImportError:
            logger.warning(
                "The requests_cache module is not installed. "
                "Ignoring N2Y_CACHE %s", n2y_cache,
            )

    if access_token is None:
        return "No NOTION_ACCESS_TOKEN environment variable is set"

    config = load_config(args.config)
    if config is None:
        return 2
    export_defaults = merge_default_config(config.get("export_defaults", {}))

    client = notion.Client(
        access_token,
        config["media_root"],
        config["media_url"],
        export_defaults=export_defaults,
    )

    error_occurred = False
    for export in config['exports']:
        logger.info("Exporting to %s", export['output'])
        client.load_plugins(export["plugins"])
        export_completed = _export_node_from_config(client, export)
        if not export_completed:
            error_occurred = True
    return 0 if not error_occurred else 3


def _export_node_from_config(client, export):
    node_type = export["node_type"]
    if node_type == "page":
        page = client.get_page(export['id'])
        if page is None:
            msg = (
                "Unable to find page with id '%s' (%s). "
                "Perhaps the integration doesn't have permission to access this page?"
            )
            logger.error(msg, export['id'], share_link_from_id(export['id']))
            return False
        result = export_page(
            page,
            export["pandoc_format"],
            export["pandoc_options"],
            export["id_property"],
            export["url_property"],
            export["property_map"],
        )
        with open(export["output"], "w") as f:
            f.write(result)
    else:
        database = client.get_database(export['id'])
        if database is None:
            msg = (
                "Unable to find database with id '%s' (%s). "
                "Perhaps the integration doesn't have permission to access this database?"
            )
            logger.error(msg, export['id'], share_link_from_id(export['id']))
            return False
        if node_type == "database_as_yaml":
            result = database_to_yaml(
                database=database,
                pandoc_format=export["pandoc_format"],
                pandoc_options=export["pandoc_options"],
                id_property=export["id_property"],
                url_property=export["url_property"],
                content_property=export["content_property"],
                notion_filter=export["notion_filter"],
                notion_sorts=export["notion_sorts"],
                property_map=export["property_map"],
            )
            result = yaml.dump(result, sort_keys=False)
            with open(export["output"], "w") as f:
                f.write(result)
        elif node_type == "database_as_files":
            database_to_markdown_files(
                database=database,
                directory=export["output"],
                pandoc_format=export["pandoc_format"],
                pandoc_options=export["pandoc_options"],
                filename_property=export["filename_property"],
                notion_filter=export["notion_filter"],
                notion_sorts=export["notion_sorts"],
                id_property=export["id_property"],
                url_property=export["url_property"],
                property_map=export["property_map"],
            )
        else:
            logger.error("Unknown node_type '%s'", node_type)
            return False
    return True


if __name__ == "__main__":
    sys.exit(main())

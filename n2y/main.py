import os
import sys
import logging
import argparse

from n2y import notion
from n2y.export import export_page, database_to_yaml, database_to_markdown_files
from n2y.config import load_config

logger = None


def cli_main():
    args = sys.argv[1:]
    access_token = os.environ.get('NOTION_ACCESS_TOKEN', None)
    sys.exit(main(args, access_token))


def main(raw_args, access_token):
    parser = argparse.ArgumentParser(
        description="Move data from Notion into YAML/markdown",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument("config", help="The path to the config file")
    parser.add_argument(
        "--verbosity", '-v', default='INFO',
        help="Level to set the root logging module to",
    )

    # TODO: Add the ability to dump out a "schema" file that contains the schema
    # for a set of databases

    # TODO: Add the ability to export everything as a sqlite file

    args = parser.parse_args(raw_args)

    logging_level = logging.__dict__[args.verbosity]
    logging.basicConfig(level=logging_level)
    global logger
    logger = logging.getLogger(__name__)

    if access_token is None:
        logger.critical('No NOTION_ACCESS_TOKEN environment variable is set')
        return 1

    config = load_config(args.config)
    if config is None:
        return 2

    client = notion.Client(access_token, config["media_root"], config["media_url"])

    for export in config['exports']:
        client.load_plugins(export["plugins"])
        node_type = export["node_type"]
        if node_type == "page":
            page = client.get_page(export['id'])
            if page is None:
                msg = (
                    "Unable to find page with id '%s'. "
                    "Perhaps the integration doesn't have permission to access this page?"
                )
                logger.error(msg, export['id'])
                continue
            result = export_page(
                page,
                export["pandoc_format"],
                export["pandoc_options"],
                export["id_property"],
                export["url_property"],
            )
            with open(export["output"], "w") as f:
                f.write(result)
        else:
            database = client.get_database(export['id'])
            if database is None:
                msg = (
                    "Unable to find database with id '%s'. "
                    "Perhaps the integration doesn't have permission to access this page?"
                )
                logger.error(msg, export['id'])
                continue
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
                )
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
                )
            else:
                logger.error("Unknown node_type '%s'", node_type)
    return 0


if __name__ == "__main__":
    cli_main()

import os
import sys
import logging
import argparse
import pkg_resources

from n2y import notion
from n2y.config import load_config
from n2y.utils import share_link_from_id, DEFAULT_MAX_RETRIES
from n2y.export import export_page, database_to_yaml, database_to_markdown_files

logger = None


def int_under_6(x):
    x = int(x)
    if x < 6:
        raise argparse.ArgumentTypeError(
            f'max_retries must be less than or equal to {DEFAULT_MAX_RETRIES}'
        )
    return x


def cli_main():
    args = sys.argv[1:]
    access_token = os.environ.get('NOTION_ACCESS_TOKEN', None)
    n2y_cache = os.environ.get('N2Y_CACHE', None)
    sys.exit(main(args, access_token, n2y_cache))


def main(raw_args, access_token, n2y_cache=None):
    parser = argparse.ArgumentParser(
        description="Move data from Notion into YAML/markdown",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument("config", help="The path to the config file")
    parser.add_argument(
        '--max_retries', '-m', default=DEFAULT_MAX_RETRIES, type=int_under_6,
        help=(
            'The maximum amount of times an API request will be retried after being rate '
            'limited. This argument must be an integer less than or equal to {DEFAULT_MAX_RETRIES}'
        )
    )
    parser.add_argument(
        "--verbosity", '-v', default='INFO',
        help="Level to set the root logging module to",
    )
    parser.add_argument(
        "--version", action='version', version=pkg_resources.require("n2y")[0].version,
        help="The version of n2y installed",
    )

    args = parser.parse_args(raw_args)

    logging_level = logging.__dict__[args.verbosity]
    stdout_handler = logging.StreamHandler(stream=sys.stdout)
    logging.basicConfig(level=logging_level, handlers=[stdout_handler])
    global logger
    logger = logging.getLogger(__name__)

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
        logger.critical('No NOTION_ACCESS_TOKEN environment variable is set')
        return 1

    config = load_config(args.config)
    if config is None:
        return 2

    client = notion.Client(
        access_token,
        config["media_root"],
        config["media_url"],
        exports=config["exports"],
        max_retries=args.max_retries
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
    cli_main()

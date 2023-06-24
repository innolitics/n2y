import os
import sys
import logging
import argparse
import pkg_resources
import yaml

from n2y import notion
from n2y.config import load_config, merge_default_config
from n2y.utils import share_link_from_id
from n2y.export import export_page, database_to_yaml, database_to_files, write_document

logger = None


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
        document = export_page(
            page,
            export["pandoc_format"],
            export["pandoc_options"],
            export["yaml_front_matter"],
            export["id_property"],
            export["url_property"],
            export["property_map"],
        )
        write_document(document, export["output"])
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
            write_document(result, export["output"])
        elif node_type == "database_as_files":
            database_to_files(
                database=database,
                directory=export["output"],
                pandoc_format=export["pandoc_format"],
                pandoc_options=export["pandoc_options"],
                yaml_front_matter=export["yaml_front_matter"],
                filename_template=export["filename_template"],
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

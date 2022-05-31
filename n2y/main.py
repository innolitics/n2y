import os
import sys
import logging
import argparse

from n2y import blocks, notion, property_values
from n2y.database import Database
from n2y.page import Page

logger = None


def cli_main():
    args = sys.argv[1:]
    access_token = os.environ.get('NOTION_ACCESS_TOKEN', None)
    sys.exit(main(args, access_token))


def main(raw_args, access_token):
    parser = argparse.ArgumentParser(
        description="Move data from Notion into YAML/markdown",
        formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("object_id", help="The id or url for a Notion database or page")
    parser.add_argument(
        "--format", '-f',
        choices=["yaml", "yaml-related", "markdown"], default="yaml",
        help=(
            "Select output type (only applies to databases)\n"
            "  yaml - log yaml to stdout\n"
            "  yaml-related - save all related databases to a set of YAML files\n"
            "  markdown - create a markdown file for each page"))
    parser.add_argument(
        "--media-root", help="Filesystem path to directory where images and media are saved")
    parser.add_argument("--media-url", help="URL for media root; must end in slash if non-empty")
    parser.add_argument("--plugins", '-p', help="Plugin file")
    parser.add_argument(
        "--output", '-o', default='./',
        help="Relative path to output directory")
    parser.add_argument(
        "--verbosity", '-v', default='INFO',
        help="Level to set the root logging module to")
    parser.add_argument(
        "--logging-format", default='%(asctime)s - %(levelname)s: %(message)s',
        help="Default format used when logging")

    # TODO: Add the ability to dump out a "schema" file that contains the schema
    # for a set of databases

    # TODO: Add the ability to export everything as a sqlite file

    args = parser.parse_args(raw_args)

    logging.basicConfig(format=args.logging_format, level=logging.__dict__[args.verbosity])
    global logger
    logger = logging.getLogger(__name__)

    if access_token is None:
        logger.critical('No NOTION_ACCESS_TOKEN environment variable is set')
        return 1

    object_id = notion.id_from_share_link(args.object_id)
    media_root = args.media_root or args.output
    if args.plugins:
        blocks.load_plugins(args.plugins)

    client = notion.Client(access_token, media_root, args.media_url)

    node = client.get_page_or_database(object_id)

    # TODO: in the future, determing the natural keys for each row in the
    # database and calculate them up-front; prune out any pages where the
    # natural key is empty. Furthermore, add duplicate handling here.

    if type(node) == Database and args.format == 'markdown':
        export_database_as_markdown_files(node, options=args)
    elif type(node) == Database and args.format == 'yaml':
        print(node.to_yaml())
    elif type(node) == Database and args.format == 'yaml-related':
        export_related_databases(node, options=args)
    elif type(node) == Page:
        print(node.to_markdown())

    return 0


def export_database_as_markdown_files(database, options):
    os.makedirs(options.output, exist_ok=True)
    seen_file_names = set()
    counts = {'unnamed': 0, 'duplicate': 0}
    for page in database.children:
        # TODO: switch to using the database's natural keys as the file names
        file_name = page.title
        if file_name:
            if file_name not in seen_file_names:
                seen_file_names.add(file_name)
                with open(os.path.join(options.output, f"{file_name}.md"), 'w') as f:
                    f.write(page.to_markdown())
            else:
                logger.warning('Skipping page named "%s" since it has been used', file_name)
                counts['duplicate'] += 1
        else:
            counts['unnamed'] += 1
    for key, count in counts.items():
        if count > 0:
            logger.info("%d %s page(s) skipped", count, key)


def export_related_databases(seed_database, options):
    os.makedirs(options.output, exist_ok=True)

    seen_database_ids = set()
    seen_file_names = set()

    def _export_related_databases(database):
        seen_database_ids.add(database.notion_id)
        file_name = database.title.to_markdown()
        if file_name not in seen_file_names:
            seen_file_names.add(file_name)
            with open(os.path.join(options.output, f"{file_name}.yml"), 'w') as f:
                f.write(database.to_yaml())
        else:
            logger.warning('Database name "%s" has been used', file_name)
        for database_id in database.related_database_ids:
            if database_id not in seen_database_ids:
                related_database = database.client.get_database(database_id)
                _export_related_databases(related_database)

    _export_related_databases(seed_database)


if __name__ == "__main__":
    cli_main()

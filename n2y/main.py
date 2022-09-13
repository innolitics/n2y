import os
import sys
import logging
import argparse

from n2y import notion
from n2y.database import Database
from n2y.page import Page
from n2y.errors import APIErrorCode, APIResponseError
from n2y.utils import id_from_share_link
from n2y.config import database_config_json_to_dict

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
    parser.add_argument("object_id", help="The id or url for a Notion database or page")
    parser.add_argument(
        "--format", '-f',
        choices=["yaml", "yaml-related", "markdown", "html"], default="yaml",
        help=(
            "Select output type (only applies to databases)\n"
            "  yaml - log yaml to stdout\n"
            "  yaml-related - save all related databases to a set of YAML files\n"
            "  markdown - create a markdown file for each page"
            "  html - create an html file for each page"
        )
    )
    parser.add_argument(
        "--content-property", default='',
        help=(
            "Store each database page's content in this property. "
            "The page's content isn't exported if it's set to a blank string. "
            "Only applies when dumping a database to YAML."
        )
    )
    parser.add_argument(
        "--id-property", default='id',
        help=(
            "Store each database page's id in this property. "
            "The page's id isn't exported if it's set to a blank string. "
        )
    )
    parser.add_argument(
        "--url-property", default='url',
        help=(
            "Store each database page's url in this property. "
            "The page's id isn't exported if it's set to a blank string. "
        )
    )
    parser.add_argument(
        "--filename-property", default=None,
        help=(
            "The database property used to generate the filename for its pages. "
            "Only applies when dumping a database to markdown files."
        )
    )
    parser.add_argument(
        "--media-root", help="Filesystem path to directory where images and media are saved"
    )
    parser.add_argument("--media-url", help="URL for media root; must end in slash if non-empty")
    parser.add_argument(
        "--plugin", '-p', action='append',
        help="Plugin module location, e.g. ('n2y.plugins.deepheaders')",
    )
    parser.add_argument(
        "--output", '-o', default='./',
        help="Relative path to output directory",
    )
    parser.add_argument(
        "--verbosity", '-v', default='INFO',
        help="Level to set the root logging module to",
    )
    parser.add_argument(
        "--logging-format", default='%(asctime)s - %(levelname)s: %(message)s',
        help="Default format used when logging",
    )
    parser.add_argument(
        "--database-config", default='{}',
        help=(
            "A JSON string in the format {database_id: {sorts: {...}, filter: {...}}}. "
            "These can be used to filter and sort databases. See "
            "https://developers.notion.com/reference/post-database-query-filter and "
            "https://developers.notion.com/reference/post-database-query-sort"
        )
    )

    # TODO: Add the ability to dump out a "schema" file that contains the schema
    # for a set of databases

    # TODO: Add the ability to export everything as a sqlite file

    args = parser.parse_args(raw_args)

    logging_level = logging.__dict__[args.verbosity]
    logging.basicConfig(format=args.logging_format, level=logging_level)
    global logger
    logger = logging.getLogger(__name__)

    if access_token is None:
        logger.critical('No NOTION_ACCESS_TOKEN environment variable is set')
        return 1

    object_id = id_from_share_link(args.object_id)
    media_root = args.media_root or args.output

    database_config = database_config_json_to_dict(args.database_config)
    valid_database_config = database_config is not None
    if not valid_database_config:
        logger.critical(
            'Database config validation failed. Please make sure you pass in '
            'a JSON string with the format {database_id: {sorts: {...}, filter: {...}}}'
        )
        return 1

    client = notion.Client(
        access_token,
        media_root,
        args.media_url,
        plugins=args.plugin,
        content_property=args.content_property,
        id_property=args.id_property,
        url_property=args.url_property,
        filename_property=args.filename_property,
        database_config=database_config,
    )

    node = client.get_page_or_database(object_id)

    if isinstance(node, Database) and args.format == 'markdown':
        export_database_as_markdown_files(node, options=args)
    if isinstance(node, Database) and args.format == 'html':
        export_database_as_html_files(node, options=args)
    elif isinstance(node, Database) and args.format == 'yaml':
        print(node.to_yaml())
    elif isinstance(node, Database) and args.format == 'yaml-related':
        export_related_databases(node, options=args)
    elif isinstance(node, Page):
        print(node.to_markdown())
    elif node is None:
        msg = (
            "Unable to find database or page with id %s. "
            "Perhaps its not shared with the integration?"
        )
        logger.error(msg, object_id)
        return 2

    return 0


def export_database_as_markdown_files(database, options):
    os.makedirs(options.output, exist_ok=True)
    seen_file_names = set()
    counts = {'unnamed': 0, 'duplicate': 0}
    for page in database.children:
        if page.filename:
            if page.filename not in seen_file_names:
                seen_file_names.add(page.filename)
                with open(os.path.join(options.output, f"{page.filename}.md"), 'w') as f:
                    f.write(page.to_markdown())
            else:
                logger.warning('Skipping page named "%s" since it has been used', page.filename)
                counts['duplicate'] += 1
        else:
            counts['unnamed'] += 1
    for key, count in counts.items():
        if count > 0:
            logger.info("%d %s page(s) skipped", count, key)


# Note these two functions are quite similar; if a third copy is needed, find a
# way to de-duplicate
def export_database_as_html_files(database, options):
    os.makedirs(options.output, exist_ok=True)
    seen_file_names = set()
    counts = {'unnamed': 0, 'duplicate': 0}
    for page in database.children:
        if page.filename:
            if page.filename not in seen_file_names:
                seen_file_names.add(page.filename)
                with open(os.path.join(options.output, f"{page.filename}.html"), 'w') as f:
                    f.write(page.to_html())
            else:
                logger.warning('Skipping page named "%s" since it has been used', page.filename)
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
        if database.filename not in seen_file_names:
            seen_file_names.add(database.filename)
            with open(os.path.join(options.output, f"{database.filename}.yml"), 'w') as f:
                f.write(database.to_yaml())
        else:
            logger.warning('Database name "%s" has been used', database.filename)
        for database_id in database.related_database_ids:
            if database_id not in seen_database_ids:
                try:
                    related_database = database.client.get_database(database_id)
                    _export_related_databases(related_database)
                except APIResponseError as err:
                    if err.code == APIErrorCode.ObjectNotFound:
                        msg = 'Skipping database with id "%s" due to lack of permissions'
                        logger.warning(msg, database_id)
                    else:
                        raise err

    _export_related_databases(seed_database)


if __name__ == "__main__":
    cli_main()

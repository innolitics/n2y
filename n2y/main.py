import os
import re
import sys
import logging
import argparse

import yaml
import pandoc

from n2y import converter, notion, simplify

logger = None


def main():
    parser = argparse.ArgumentParser(
        description="Move data from Notion into YAML/markdown",
        formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("object_id", help="The id or url for a Notion database or page")
    parser.add_argument(
        "--format", '-f',
        choices=["yaml", "markdown"], default="yaml",
        help=(
            "Select output type\n"
            "  yaml - log yaml to stdout\n"
            "  markdown - create a markdown file for each page"))
    parser.add_argument("--image-path", help="Specify path where to save images")
    parser.add_argument("--image-web-path", help="Web path for images")
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
    parser.add_argument(
        "--name-column", '-n', default='title',
        help=(
            "Database column that will be used to generate the filename "
            "for each row. Column names are normalized to lowercase letters, "
            "numbers, and underscores. Only used when generating markdown."))
    args = parser.parse_args()

    logging.basicConfig(
        format=args.logging_format, level=logging.__dict__[args.verbosity])
    global logger
    logger = logging.getLogger(__name__)

    ACCESS_TOKEN = os.environ.get('NOTION_ACCESS_TOKEN', None)
    if ACCESS_TOKEN is None:
        logger.critical('No NOTION_ACCESS_TOKEN environment variable is set')
        return 1

    object_id = notion.id_from_share_link(args.object_id)
    if not args.image_path:
        args.image_path = args.output
    converter.IMAGE_PATH = args.image_path
    converter.IMAGE_WEB_PATH = args.image_web_path
    if args.plugins:
        converter.load_plugins(args.plugins)

    client = notion.Client(ACCESS_TOKEN)

    # TODO: get database OR page
    raw_rows = client.get_database(object_id)

    # TODO: in the future, determing the natural keys for each row in the
    # database and calculate them up-front; prune out any pages where the
    # natural key is empty. Furthermore, add duplicate handling here. Once the
    # natural key handling is done, there should be no need for the
    # `name_column_valid` since that will be handled here

    if args.output == 'markdown':
        if name_column_valid(raw_rows, args.name_column):
            export_database_as_markdown_files(client, raw_rows, options=args)
        else:
            return 1
    elif args.output == 'yaml':
        export_database_as_yaml_file(client, raw_rows)

    return 0


def name_column_valid(raw_rows, name_column):
    first_row_flattened = simplify.flatten_database_row(raw_rows[0])

    def available_columns():
        return filter(
            lambda c: isinstance(first_row_flattened[c], str),
            first_row_flattened.keys())

    # make sure the title column exists
    if name_column not in first_row_flattened:
        logger.critical(
            'Database does not contain the column "%s". Please specify '
            'the correct name column using the --name-column (-n) flag. '
            # only show columns that have strings as possible options
            'Available column(s): ' + ', '.join(available_columns()), name_column)
        return False

    # make sure title column is not empty (only the first row is checked)
    if first_row_flattened[name_column] is None:
        logger.critical('Column "%s" Cannot Be Empty.', name_column)
        return False

    # make sure the title column is a string
    if not isinstance(first_row_flattened[name_column], str):
        logger.critical(
            'Column "%s" does not contain a string. '
            # only show columns that have strings as possible options
            'Available column(s): ' + ', '.join(available_columns()), name_column)
        return False
    return True


def export_database_as_markdown_files(client, raw_rows, options):
    os.makedirs(options.output, exist_ok=True)
    file_names = []
    skips = {'unnamed': 0, 'duplicate': 0}
    for row in raw_rows:
        meta = simplify.flatten_database_row(row)
        page_name = meta[options.name_column]
        if page_name:
            # sanitize file name just a bit
            # maybe use python-slugify in the future?
            filename = re.sub(r"[\s/,\\]", '_', page_name.lower())
            if filename not in file_names:
                file_names.append(filename)

                pandoc_output = converter.load_block(client, row['id']).to_pandoc()
                logger.info('Processing page "%s".', page_name)

                markdown = pandoc_tree_to_markdown(pandoc_output)

                with open(os.path.join(options.output, f"{filename}.md"), 'w') as f:
                    f.write('---\n')
                    f.write(yaml.dump(meta))
                    f.write('---\n\n')
                    f.write(markdown)
            else:
                logger.debug('Page name "%s" has been used', page_name)
                skips['duplicate'] += 1
        else:
            skips['unnamed'] += 1
    for key, count in skips.items():
        if count > 0:
            logger.info("%d %s page(s) skipped", count, key)


def export_database_as_yaml_file(client, raw_rows):
    result = []
    for row in raw_rows:
        pandoc_output = converter.load_block(client, row['id']).to_pandoc()
        markdown = pandoc_tree_to_markdown(pandoc_output) if pandoc_output else None
        result.append({**simplify.flatten_database_row(row), 'content': markdown})

    print(yaml.dump(result, sort_keys=False))


def pandoc_tree_to_markdown(pandoc_tree):
    return pandoc.write(pandoc_tree, format='gfm+tex_math_dollars') \
        .replace('\r\n', '\n')  # Deal with Windows line endings


if __name__ == "__main__":
    sys.exit(main())

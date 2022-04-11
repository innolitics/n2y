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
    parser.add_argument("database", help="The Notion database id or share url")
    parser.add_argument(
        "--output", '-o',
        choices=["yaml", "markdown"], default="yaml",
        help=(
            "Select output type\n"
            "  yaml - log yaml to stdout\n"
            "  markdown - create a markdown file for each page"))
    parser.add_argument("--image-path", '-ip', help="Specify path where to save images")
    parser.add_argument("--image-web-path", '-iw', help="Web path for images")
    parser.add_argument("--plugins", '-p', help="Plugin file")
    parser.add_argument(
        "--target", '-t', default='./',
        help="Relative path to target directory")
    parser.add_argument(
        "--verbosity", '-v', default='INFO',
        help="Level to set the root logging module to")
    parser.add_argument(
        "--logging-format", '-f', default='%(asctime)s - %(levelname)s: %(message)s',
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

    database_id = notion.id_from_share_link(args.database)
    if not args.image_path:
        args.image_path = args.target
    converter.IMAGE_PATH = args.image_path
    converter.IMAGE_WEB_PATH = args.image_web_path
    if args.plugins:
        converter.load_plugins(args.plugins)

    client = notion.Client(ACCESS_TOKEN)

    raw_rows = client.get_database(database_id)
    if args.output == 'markdown':
        if name_column_valid(raw_rows, args.name_column):
            export_markdown(client, raw_rows, options=args)
        else:
            return 1
    elif args.output == 'yaml':
        export_yaml(client, raw_rows)

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


def export_markdown(client, raw_rows, options):
    file_names = []
    skips = {'empty': 0, 'unnamed': 0, 'duplicate': 0}
    for row in raw_rows:
        meta = simplify.flatten_database_row(row)
        page_name = meta[options.name_column]
        if page_name:
            filename = re.sub(r"[\s/,\\]", '_', page_name.lower())
            if filename not in file_names:
                file_names.append(filename)

                pandoc_output = converter.load_block(client, row['id']).to_pandoc()
                # do not create markdown pages if there is no page in Notion
                if pandoc_output:
                    logger.info('Processing page "%s".', page_name)
                    markdown = pandoc.write(pandoc_output, format='gfm+tex_math_dollars') \
                        .replace('\r\n', '\n')  # Deal with Windows line endings

                    os.makedirs(options.target, exist_ok=True)

                    # sanitize file name just a bit
                    # maybe use python-slugify in the future?
                    with open(os.path.join(options.target, f"{filename}.md"), 'w') as f:
                        f.write('---\n')
                        f.write(yaml.dump(meta))
                        f.write('---\n\n')
                        f.write(markdown)
                else:
                    logger.debug('Skipping page "%s" because it is empty.', page_name)
                    skips['empty'] += 1
            else:
                logger.debug(
                    'Skipping page "%s" because that name has already'
                    ' been used. Please rename.', page_name)
                skips['duplicate'] += 1
        else:
            logger.debug("Skipping page with no name.")
            skips['unnamed'] += 1
    msg = ""
    types_skipped = 0
    prefixes = ("", " & ", ", & ")
    for key in skips.keys():
        count = skips[key]
        if count > 0:
            msg = msg if key != "duplicate" and types_skipped < 2 else msg.replace(" &", ",")
            msg += f"{prefixes[types_skipped]}{count} {key}"
            types_skipped += 1

    msg == "" or logger.info("%s page(s) skipped", msg)


def export_yaml(client, raw_rows):
    result = []
    for row in raw_rows:
        pandoc_output = converter.load_block(client, row['id']).to_pandoc()
        markdown = pandoc.write(pandoc_output, format='gfm') if pandoc_output else None
        result.append({**simplify.flatten_database_row(row), 'content': markdown})

    print(yaml.dump(result, sort_keys=False))


if __name__ == "__main__":
    sys.exit(main())

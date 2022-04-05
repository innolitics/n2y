import os
import re
import sys
import yaml
import pandoc
import logging
import argparse
from n2y import converter, notion, simplify

logger = logging.getLogger('n2y.main')


def main():
    parser = argparse.ArgumentParser(
        description="Move data from Notion into YAML/markdown",
        formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("database", help="The Notion database id or share url")
    parser.add_argument("--output", '-o',
                        choices=["yaml", "markdown"], default="yaml",
                        help=(
                            "Select output type\n"
                            "  yaml - log yaml to stdout\n"
                            "  markdown - create a markdown file per page"))
    parser.add_argument("--image-path", help="Specify path where to save images")
    parser.add_argument("--image-web-path", help="Web path for images")
    parser.add_argument("--plugins", help="Plugin file")
    parser.add_argument("--target", '-t', default='./',
                        help="relative path to target directory")
    parser.add_argument("--name-column", default='title',
                        help=(
                            "Database column that will be used to generate the filename "
                            "for each row. Column names are normalized to lowercase letters, "
                            "numbers, and underscores. Only used when generating markdown."))
    args = parser.parse_args()

    ACCESS_TOKEN = os.environ.get("NOTION_ACCESS_TOKEN", None)
    if ACCESS_TOKEN is None:
        logger.error("ERROR: No NOTION_ACCESS_TOKEN environment variable is set")
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
        raise NotImplementedError("%s%s%s" % (
            f"ERROR: Database Does Not Contain The Column \"{name_column}\".\n",
            "Please Specify The Correct Name Column Using The --name-column Flag.\n",
            # only show columns that have strings as possible options
            "Available Column(s): " + ", ".join(available_columns())))

    # make sure title column is not empty (only the first row is checked)
    if first_row_flattened[name_column] is None:
        raise NotImplementedError(f"ERROR: Column \"{name_column}\" Cannot Be Empty.")

    # make sure the title column is a string
    if not isinstance(first_row_flattened[name_column], str):
        raise NotImplementedError("%s%s" % (
            f"ERROR: Column \"{name_column}\" Does Not Contain A String.\n",
            # only show columns that have strings as possible options
            "Available Column(s): " + ", ".join(available_columns())))
    return True


def export_markdown(client, raw_rows, options):
    file_names = []
    skips = {'Empty': 0, 'Unnamed': 0, 'Duplicate': 0}
    for row in raw_rows:
        meta = simplify.flatten_database_row(row)
        page_name = meta[options.name_column]
        if page_name is not None:
            filename = re.sub(r"[\s/,\\]", '_', page_name.lower())
            if filename not in file_names:
                file_names.append(filename)

                pandoc_output = converter.load_block(client, row['id']).to_pandoc()
                # do not create markdown pages if there is no page in Notion
                if pandoc_output:
                    logger.warning(f'Processing Page "{meta[options.name_column]}"')
                    markdown = pandoc.write(pandoc_output, format='gfm+tex_math_dollars') \
                        .replace('\r\n', '\n')  # Deal with Windows line endings

                    # create target path if it doesn't exist
                    # if not os.path.exists(options.target):
                    os.makedirs(options.target, exist_ok=True)

                    # sanitize file name just a bit
                    # maybe use python-slugify in the future?
                    with open(os.path.join(options.target, f"{filename}.md"), 'w') as f:
                        f.write('---\n')
                        f.write(yaml.dump(meta))
                        f.write('---\n\n')
                        f.write(markdown)
                else:
                    logger.debug(f"Skipping Empty Page: {page_name}")
                    skips['Empty'] += 1
            else:
                logger.debug(
                    "%s %s",
                    f'Skipping Empty Page: "{page_name}",',
                    'Name Has Already Been Used. Please Rename')
                skips['Duplicate'] += 1
        else:
            logger.debug("Skipping Page With No Name")
            skips['Unnamed'] += 1
    msg = ""
    types_skipped = 0
    prefixes = ("", " & ", ", & ")
    for key in skips.keys():
        count = skips[key]
        if count > 0:
            msg = msg if key != "Duplicate" and types_skipped < 2 else msg.replace(" &", ",")
            msg += f"{prefixes[types_skipped]}{count} {key}"
            types_skipped += 1

    msg == "" or logger.warning(f"WARNING: {msg} Page(s) Skipped")


def export_yaml(client, raw_rows):
    result = []
    for row in raw_rows:
        pandoc_output = converter.load_block(client, row['id']).to_pandoc()
        markdown = pandoc.write(pandoc_output, format='gfm') if pandoc_output else None
        result.append({**simplify.flatten_database_row(row), 'content': markdown})

    logger.info(yaml.dump(result, sort_keys=False))


if __name__ == "__main__":
    sys.exit(main())

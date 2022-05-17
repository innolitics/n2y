import os
import re
import sys
import logging
import argparse

import yaml
import pandoc

from n2y import blocks, notion, property_values

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
        choices=["yaml", "markdown"], default="yaml",
        help=(
            "Select output type (only applies to databases)\n"
            "  yaml - log yaml to stdout\n"
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
    parser.add_argument(
        "--name-column", '-n', default='title',
        help=(
            "Database column that will be used to generate the filename "
            "for each row. Column names are normalized to lowercase letters, "
            "numbers, and underscores. Only used when generating markdown."))
    args = parser.parse_args(raw_args)

    logging.basicConfig(
        format=args.logging_format, level=logging.__dict__[args.verbosity])
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

    object_data, object_type = client.get_page_or_database(object_id)

    # TODO: in the future, determing the natural keys for each row in the
    # database and calculate them up-front; prune out any pages where the
    # natural key is empty. Furthermore, add duplicate handling here. Once the
    # natural key handling is done, there should be no need for the
    # `name_column_valid` since that will be handled here

    if object_type == "database" and args.format == 'markdown':
        if name_column_valid(object_data, args.name_column):
            export_database_as_markdown_files(client, object_data, options=args)
        else:
            return 1
    elif object_type == "database" and args.format == 'yaml':
        export_database_as_yaml_file(client, object_data)
    elif object_type == "page":
        export_page_as_markdown(client, object_data)

    return 0


def name_column_valid(raw_rows, name_column):
    first_row_flattened = property_values.flatten_property_values(raw_rows[0])

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
        meta = property_values.flatten_property_values(row)
        page_name = meta[options.name_column]
        if page_name:
            # sanitize file name just a bit
            # maybe use python-slugify in the future?
            filename = re.sub(r"[\s/,\\]", '_', page_name.lower())
            if filename not in file_names:
                file_names.append(filename)

                pandoc_output = blocks.load_block(client, row['id']).to_pandoc()
                logger.info('Processing page "%s".', page_name)

                markdown = pandoc_tree_to_markdown(pandoc_output)

                with open(os.path.join(options.output, f"{filename}.md"), 'w') as f:
                    write_yaml_frontmatter(f, meta)
                    f.write(markdown)
            else:
                logger.debug('Page name "%s" has been used', page_name)
                skips['duplicate'] += 1
        else:
            skips['unnamed'] += 1
    for key, count in skips.items():
        if count > 0:
            logger.info("%d %s page(s) skipped", count, key)


def write_yaml_frontmatter(open_file, metadata):
    open_file.write('---\n')
    # TODO: replace with nice clean YAML dumper
    open_file.write(yaml.dump(metadata))
    open_file.write('---\n\n')


def export_database_as_yaml_file(client, raw_rows):
    result = []
    for row in raw_rows:
        pandoc_output = blocks.load_block(client, row['id']).to_pandoc()
        markdown = pandoc_tree_to_markdown(pandoc_output) if pandoc_output else None
        result.append({**property_values.flatten_property_values(row), 'content': markdown})

    print(yaml.dump(result, sort_keys=False))


def export_page_as_markdown(client, page):
    pandoc_output = blocks.load_block(client, page['id']).to_pandoc()
    markdown = pandoc_tree_to_markdown(pandoc_output) if pandoc_output else None
    metadata = property_values.flatten_property_values(page)

    # For now, print the single page to standard output; eventually we'll need
    # to re-think this and likely write the result to a file. This is necessary
    # if there are sub-pages or sub-databases which would need to go into
    # separate files.
    write_yaml_frontmatter(sys.stdout, metadata)
    print(markdown)


def pandoc_tree_to_markdown(pandoc_tree):
    return pandoc.write(pandoc_tree, format='gfm+tex_math_dollars') \
        .replace('\r\n', '\n')  # Deal with Windows line endings


if __name__ == "__main__":
    cli_main()

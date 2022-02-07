import os
import sys
import argparse
import re

import yaml
import pandoc

from n2y import converter, notion, simplify


def main():
    parser = argparse.ArgumentParser(description="Move data from Notion into YAML/markdown",
                                     formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("database", help="The Notion database id or share url")
    parser.add_argument("--output", '-o',
                        choices=["yaml", "markdown"], default="yaml",
                        help=("Select output type\n"
                              "  yaml - print yaml to stdout\n"
                              "  markdown - create a mardown file per page"))
    parser.add_argument("--image-path", help="Specify path where to save images")
    parser.add_argument("--image-web-path", help="web path for images")
    parser.add_argument("--plugins", help="plugin file")
    parser.add_argument("--name-column", default='title',
                        help=("Name of column containing the page name."
                              "Lowercase letter and numbers. Replace spaces with underscore."))
    args = parser.parse_args()

    ACCESS_TOKEN = os.environ.get("NOTION_ACCESS_TOKEN", None)
    if ACCESS_TOKEN is None:
        print("No NOTION_ACCESS_TOKEN environment variable is set", file=sys.stderr)
        return 1

    database_id = notion.id_from_share_link(args.database)

    converter.IMAGE_PATH = args.image_path
    converter.IMAGE_WEB_PATH = args.image_web_path
    if args.plugins:
        converter.load_plugins(args.plugins)

    client = notion.Client(ACCESS_TOKEN)

    if args.output == 'markdown':
        export_markdown(client, database_id, options=args)
    elif args.output == 'yaml':
        export_yaml(client, database_id, options=args)

    return 0


def export_markdown(client, database_id, options):
    raw_rows = client.get_database(database_id)

    if options.name_column not in raw_rows[0]:
        print(f"Database does not contain the column \"{options.name_column}\". "
              f"Please specify the correct name column using the --name-column flag.")
        exit(1)

    for row in raw_rows:
        meta = simplify.flatten_database_row(row)
        print(f"Processing {meta[options.name_column]}", file=sys.stderr)
        markdown = pandoc.write(
            converter.load_block(client, row['id']).to_pandoc(), format='gfm') \
            .replace('\r\n', '\n')  # Deal with Windows line endings
        # sanitize file name just a bit
        # maybe use python-slugify in the future?
        filename = re.sub(r"[/,\\]", '_', meta[options.name_column].lower())
        with open(f"{filename}.md", 'w') as f:
            f.write('---\n')
            f.write(yaml.dump(meta))
            f.write('---\n\n')
            f.write(markdown)


def export_yaml(client, database_id, options):
    raw_rows = client.get_database(database_id)

    if not options.name_column in simplify.flatten_database_row(raw_rows[0]):
        print(f"Database does not contain the column \"{options.name_column}\". "
              f"Please specify the correct name column using the --name-column flag.")
        exit(1)

    # result = [{options.name_column: None, **simplify.flatten_database_row(row),
    #           'content':
    #            (pandoc.write(converter.load_block(client, row['id']).to_pandoc(),
    #                          format='gfm') if row['has_children'] else None)}
    #           for row in raw_rows]
    result = []
    for row in raw_rows:
        pandoc_output = converter.load_block(client, row['id']).to_pandoc()
        markdown = pandoc.write(pandoc_output, format='gfm') if pandoc_output else None
        result.append({options.name_column: None,
                       **simplify.flatten_database_row(row),
                       'content': markdown})

    print(yaml.dump_all(result, sort_keys=False))


if __name__ == "__main__":
    sys.exit(main())

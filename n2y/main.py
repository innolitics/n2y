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
                              "  markdown - create a markdown file per page"))
    parser.add_argument("--image-path", help="Specify path where to save images")
    parser.add_argument("--image-web-path", help="Web path for images")
    parser.add_argument("--plugins", help="Plugin file")
    parser.add_argument("--target", '-t', default='./',
                        help="relative path to target directory")
    parser.add_argument("--name-column", default='title',
                        help=("Name of column containing the page name."
                              "Lowercase letter and numbers. Replace spaces with underscore."))
    args = parser.parse_args()

    ACCESS_TOKEN = os.environ.get("NOTION_ACCESS_TOKEN", None)
    if ACCESS_TOKEN is None:
        print("No NOTION_ACCESS_TOKEN environment variable is set", file=sys.stderr)
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
    first_row_flattened = simplify.flatten_database_row(raw_rows[0])

    def available_columns():
        return filter(lambda c: isinstance(first_row_flattened[c], str),
                      first_row_flattened.keys())

    # make sure the title column exists
    if args.name_column not in first_row_flattened:
        print(f"Database does not contain the column \"{args.name_column}\". "
              f"Please specify the correct name column using the --name-column flag.",
              file=sys.stderr)
        print("Available column(s): ",
              # only show columns that have strings as possible options
              ", ".join(available_columns()), file=sys.stderr)
        return 1

    # make sure title column is not empty (only the first row is checked)
    if first_row_flattened[args.name_column] is None:
        print(f"Column \"{args.name_column}\" cannot be empty.", file=sys.stderr)
        return 1

    # make sure the title column is a string
    if not isinstance(first_row_flattened[args.name_column], str):
        print(f"Column \"{args.name_column}\" does not contain a string.", file=sys.stderr)
        print("Available column(s): ",
              # only show columns that have strings as possible options
              ", ".join(available_columns()), file=sys.stderr)
        return 1

    if args.output == 'markdown':
        export_markdown(client, raw_rows, options=args)
    elif args.output == 'yaml':
        export_yaml(client, raw_rows, options=args)

    return 0


def export_markdown(client, raw_rows, options):
    file_names = []
    for row in raw_rows:
        meta = simplify.flatten_database_row(row)
        page_name = meta[options.name_column]
        filename = re.sub(r"[/,\\]", '_', page_name.lower())
        if page_name is not None:
            print(f"Processing {meta[options.name_column]}", file=sys.stderr)
            if filename in file_names:
                print(f'WARNING: duplicate file name "{filename}.md"', file=sys.stderr)
            file_names.append(filename)

            pandoc_output = converter.load_block(client, row['id']).to_pandoc()
            # do not create markdown pages if there is no page in Notion
            if pandoc_output:
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
                print(f"WARNING: skipping empty page: {page_name}", file=sys.stderr)
        else:
            print("WARNING: skipping page with no name", file=sys.stderr)


def export_yaml(client, raw_rows, options):
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

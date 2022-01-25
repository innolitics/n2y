import os
import sys
import argparse
import re

import yaml
import pandoc

from n2y import converter, notion, simplify


def main():
    ACCESS_TOKEN = os.environ.get("NOTION_ACCESS_TOKEN", None)
    if ACCESS_TOKEN is None:
        print("No NOTION_ACCESS_TOKEN environment variable is set", file=sys.stderr)
        return 1

    parser = argparse.ArgumentParser(description="Move data from Notion into YAML files")
    parser.add_argument("database", help="The Notion database id or share url")
    # Is this still needed?
    #
    # parser.add_argument(
    #     "--raw", action='store_true',
    #     help="Dump the raw notion API data",
    # )
    parser.add_argument("--image-path", help="Specify path where to save images")
    parser.add_argument("--image-web-path", help="web path for images")
    parser.add_argument("--plugins", help="plugin file")
    args = parser.parse_args()
    database_id = notion.id_from_share_link(args.database)

    converter.IMAGE_PATH = args.image_path
    converter.IMAGE_WEB_PATH = args.image_web_path
    if args.plugins:
        converter.load_plugins(args.plugins)

    client = notion.Client(ACCESS_TOKEN)
    raw_rows = client.get_database(database_id)

    for row in raw_rows:
        meta = simplify.flatten_database_row(row)
        print(f"Processing {meta['title']}")
        markdown = pandoc.write(
            converter.load_block(client, row['id']).to_pandoc()) \
            .replace('\r\n', '\n')  # Deal with Windows line endings
        # sanitize file name just a bit
        # maybe use python-slugify in the future?
        filename = re.sub(r"[/,\\]", '_', meta['title'].lower())
        with open(f"{filename}.md", 'w') as f:
            f.write('---\n')
            f.write(yaml.dump(meta))
            f.write('---\n\n')
            f.write(markdown)
    return 0


if __name__ == "__main__":
    sys.exit(main())

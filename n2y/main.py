import os
import sys
import argparse
import re

import yaml
import pandoc

from n2y import notion, simplify, converter


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
    args = parser.parse_args()
    database_id = notion.id_from_share_link(args.database)
    client = notion.Client(ACCESS_TOKEN)
    raw_rows = client.get_database(database_id)

    for row in raw_rows:
        meta = simplify.flatten_database_row(row)
        print(f"Processing {meta['title']}")
        markdown = pandoc.write(
            converter.convert({'content': client.get_page(row['id'])}), format='gfm')\
            .replace('\r\n', '\n')  # Deal with Windows line endings
        # sanitize file name just a bit
        # maybe use python-slugify in the future?
        filename = re.sub(r"[/,\\]", '_', meta['title'])
        with open(f"{filename}.md", 'w') as f:
            f.write('---\n')
            f.write(yaml.dump(meta))
            f.write('---\n\n')
            f.write(markdown)
    return 0


if __name__ == "__main__":
    sys.exit(main())

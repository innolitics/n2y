import os
import sys
import argparse

import yaml

from n2y import notion, simplify


def main():
    ACCESS_TOKEN = os.environ.get("NOTION_ACCESS_TOKEN", None)
    if ACCESS_TOKEN is None:
        print("No NOTION_ACCESS_TOKEN environment variable is set", file=sys.stderr)
        return 1

    parser = argparse.ArgumentParser(description="Move data from Notion into YAML files")
    parser.add_argument("database", help="The Notion database id or share url")
    parser.add_argument(
        "--raw", action='store_true',
        help="Dump the raw notion API data",
    )
    args = parser.parse_args()
    database_id = notion.id_from_share_link(args.database)
    client = notion.Client(ACCESS_TOKEN)
    raw_rows = client.get_database(database_id)
    if args.raw:
        print(yaml.dump(raw_rows))
        return 0

    simplified_rows = simplify.flatten_database_rows(raw_rows)
    print(yaml.dump(simplified_rows))
    return 0


if __name__ == "__main__":
    sys.exit(main())

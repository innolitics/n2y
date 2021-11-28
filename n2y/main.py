import os
import sys
import argparse

import yaml

from n2y import notion

def main():
    ACCESS_TOKEN = os.environ.get("NOTION_ACCESS_TOKEN", None)
    if ACCESS_TOKEN is None:
        print("No NOTION_ACCESS_TOKEN environment variable is set", file=sys.stderr)
        sys.exit(1)

    parser = argparse.ArgumentParser(description="Move data from Notion into YAML files")
    parser.add_argument("database", help="The Notion database id or share url")
    args = parser.parse_args()
    database_id = notion.id_from_share_link(args.database)
    client = notion.Client(ACCESS_TOKEN)
    database_data = client.get_database(database_id)
    print(yaml.dump(database_data))


if __name__ == "__main__":
    main()

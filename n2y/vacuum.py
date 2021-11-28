import os
import sys
import argparse

BASE_NOTION_API_URL = "https://api.notion.com"

if __name__ == "__main__":
    ACCESS_TOKEN = os.environ.get("NOTION_ACCESS_TOKEN", None)
    if ACCESS_TOKEN is None:
        print("No NOTION_ACCESS_TOKEN environment variable is set", file=sys.stderr)
        sys.exit(1)

    DATABASE_ID = sys.argv[1]
    if ACCESS_TOKEN is None:
        print("No NOTION_ACCESS_TOKEN environment variable is set", file=sys.stderr)
        sys.exit(1)

    # get environment variable for notion
    # get database name from first arg
    # pipe result to a YAML file

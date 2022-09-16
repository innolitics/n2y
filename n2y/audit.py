import os
import sys
import logging
import argparse

from n2y import notion
from n2y.database import Database
from n2y.blocks import LinkToPageBlock
from n2y.errors import UseNextClass
from n2y.page import Page
from n2y.utils import id_from_share_link
from n2y.mentions import PageMention

logger = None


plugin_key = "audit"


class ReportingPageMention(PageMention):
    def __init__(self, client, notion_data, plain_text, block=None):
        if block is None:
            raise UseNextClass()
        super().__init__(client, notion_data, plain_text, block)
        if plugin_key not in block.page.plugin_data:
            block.page.plugin_data[plugin_key] = []
        block.page.plugin_data[plugin_key].append({
            "block_url": block.notion_url,
            "linked_page_id": self.notion_page_id,
            "type": "page mention",
        })


class ReportingLinkToPageBlock(LinkToPageBlock):
    def __init__(self, client, notion_data, page, get_children=True):
        super().__init__(client, notion_data, page, get_children)
        if plugin_key not in page.plugin_data:
            page.plugin_data[plugin_key] = []
        page.plugin_data[plugin_key].append({
            "block_url": self.notion_url,
            "linked_page_id": self.linked_page_id,
            "type": "link to page",
        })


def cli_main():
    args = sys.argv[1:]
    access_token = os.environ.get('NOTION_ACCESS_TOKEN', None)
    sys.exit(main(args, access_token))


def main(raw_args, access_token):
    parser = argparse.ArgumentParser(
        description="Audit a set of Notion pages for external links",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument("object_id", help="The id or url for a Notion database or page")
    parser.add_argument(
        "--verbosity", '-v', default='INFO',
        help="Level to set the root logging module to",
    )
    parser.add_argument(
        "--logging-format", default='%(asctime)s - %(levelname)s: %(message)s',
        help="Default format used when logging",
    )

    args = parser.parse_args(raw_args)

    logging_level = logging.__dict__[args.verbosity]
    logging.basicConfig(format=args.logging_format, level=logging_level)
    global logger
    logger = logging.getLogger(__name__)

    if access_token is None:
        logger.critical('No NOTION_ACCESS_TOKEN environment variable is set')
        return 1

    object_id = id_from_share_link(args.object_id)

    # TODO: handle synced blocks (need to upgrade the API version first so we
    # can go from synced-block to primary synced block then up to the page;
    # going up to the page from the other synced block isn't possible in the
    # 2022-02-22 API version)

    # TODO: handle plain old links to other pages
    # TODO: handle at-mentions outside of blocks
    plugins = {
        "mentions": {
            "page": ReportingPageMention,
        },
        "blocks": {
            "link_to_page": ReportingLinkToPageBlock,
        },
    }

    client = notion.Client(access_token)
    client.load_plugin(plugins)

    node = client.get_page_or_database(object_id)

    if node is None:
        msg = (
            "Unable to find database or page with id %s. "
            "Perhaps its not shared with the integration?"
        )
        logger.error(msg, object_id)
        return 2

    references = {}
    audit_node(node, references, 0)
    external_references = exclude_internal_references(references)
    print_references(client, external_references)
    if any(len(l) for l in external_references.values()):
        return 3
    else:
        return 0


def exclude_internal_references(references):
    external_references = {}
    for page_id, links in references.items():
        external_links = [l for l in links if l['linked_page_id'] not in references]
        external_references[page_id] = external_links
    return external_references


def print_references(client, references):
    for page_id, links in references.items():
        if not links:
            continue
        page = client.get_page(page_id)
        print(page.title.to_plain_text())
        for link in links:
            print("  " + link["block_url"])


def audit_node(node, references, depth):
    if isinstance(node, Database):
        audit_database(node, references, depth)
    elif isinstance(node, Page):
        audit_page(node, references, depth)


def audit_database(database, references, depth):
    logger.info("%sDatabase %s", " " * depth, database.title.to_plain_text())
    for page in database.children:
        audit_page(page, references, depth + 1)


def audit_page(page, references, depth):
    logger.info("%sAuditing %s", " " * depth, page.title.to_plain_text())
    assert page.notion_id not in references  # expect that each page is visited once
    page.block  # load all of the blocks
    references[page.notion_id] = page.plugin_data.get(plugin_key, [])
    for node in page.children:
        audit_node(node, references, depth + 1)


if __name__ == "__main__":
    cli_main()

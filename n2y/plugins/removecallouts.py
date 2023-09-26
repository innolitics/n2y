from n2y.blocks import NoopBlock


class RemoveCalloutBlock(NoopBlock):
    """
    Completely removes callout blocks from the generated content.

    Useful, e.g., if you want callout blocks to contain help text that shouldn't
    be included in generated documents.
    """

    ...


notion_classes = {
    "blocks": {
        "callout": RemoveCalloutBlock,
    }
}

from n2y.blocks import CalloutBlock


class RemoveCalloutBlock(CalloutBlock):
    """
    Completely removes callout blocks from the generated content.

    Useful, e.g., if you want callout blocks to contain help text that shouldn't
    be included in generated documents.
    """

    def __init__(self, client, notion_data, page, get_children=True):
        pass

    def to_pandoc(self):
        # It should be possible to return `pandoc.types.Null`, but that didn't
        # seem to work due to `TypeError: Object of type MetaType is not JSON serializable`
        # TODO: investigate why and simplify Block.children_to_pandoc if it can
        # be supported.
        return None


notion_classes = {
    "blocks": {
        "callout": RemoveCalloutBlock,
    }
}

from pandoc.types import Div, BlockQuote
from n2y.blocks import QuoteBlock


class NotionQuoteBlock(QuoteBlock):
    """
    Handler for Notion quote blocks that preserves Notion's styling.
    """

    def __init__(self, client, notion_data, page, get_children=True):
        super().__init__(client, notion_data, page, get_children)
        self.notion_color = self._extract_notion_color()

    def _extract_notion_color(self):
        """Extract color information from Notion block data"""
        try:
            if hasattr(self.notion_data, 'quote') and self.notion_data.quote:
                return getattr(self.notion_data.quote, 'color', 'default')
            return 'default'
        except:
            return 'default'

    def to_pandoc(self):
        # Get the regular BlockQuote content from parent class
        quote_content = super().to_pandoc()

        # Since Pandoc doesn't support attributes on BlockQuote, 
        # use a Div with blockquote styling classes for visual compatibility
        if isinstance(quote_content, BlockQuote):
            # Extract the content from the original BlockQuote
            content = quote_content[0]  # BlockQuote content (list of blocks)
        elif isinstance(quote_content, list):
            content = quote_content
        else:
            content = [quote_content]

        # Create a Div with both DOCX custom-style AND CSS classes for web compatibility
        return Div(
            ("", ["blockquote", "notion-quote"], [("custom-style", "Block Quote")]), 
            content
        )


notion_classes = {
    "blocks": {
        "quote": NotionQuoteBlock,
    }
}

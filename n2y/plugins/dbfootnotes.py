import logging

from pandoc.types import Note

from n2y.database import Database
from n2y.errors import UseNextClass
from n2y.mentions import PageMention

plugin_data_key = "n2y.plugins.dbfootnotes"

logger = logging.getLogger(__name__)


class PageMentionFootnote(PageMention):
    def __init__(self, client, notion_data, plain_text, block=None):
        super().__init__(client, notion_data, plain_text, block)
        if (
            self._get_mention_page()
            and self._get_mention_page_parent()
            and self._is_footnote()
        ):
            self._attach_footnote()
        else:
            raise UseNextClass

    def _get_mention_page(self):
        self.mentioned_page = self.client.get_page(self.notion_page_id)
        return self.mentioned_page is not None

    def _get_mention_page_parent(self):
        self.mentioned_page_parent = self.mentioned_page.parent
        return self.mentioned_page_parent is not None

    def _is_footnote(self):
        if isinstance(self.mentioned_page_parent, Database):
            return self.mentioned_page_parent.title.to_plain_text().endswith(
                "Footnotes"
            )
        else:
            return False

    def _attach_footnote(self):
        block_content = self.mentioned_page.block.children_to_pandoc()
        self._footnote_in_pandoc_ast = (
            Note(block_content)
            if isinstance(block_content, list)
            else Note([block_content])
        )

    def to_pandoc(self):
        return [self._footnote_in_pandoc_ast]


notion_classes = {"mentions": {"page": PageMentionFootnote}}

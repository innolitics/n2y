import logging

from pandoc.types import Note

from n2y.database import Database
from n2y.errors import PluginError, UseNextClass
from n2y.mentions import PageMention

plugin_data_key = "n2y.plugins.dbfootnotes"

logger = logging.getLogger(__name__)


class PageMentionFootnote(PageMention):
    def __init__(self, client, notion_data, plain_text, block):
        super().__init__(client, notion_data, plain_text, block)
        if block is not None and self._references_correct() and self._is_footnote():
            self._attach_footnote()
        else:
            raise UseNextClass

    def _get_mention(self):
        # This should be the footnote content page.
        self.mentioned_page = self.client.get_page(self.notion_page_id)
        return self.mentioned_page is not None

    def _get_parents(self):
        # This should be the inline database.
        self.mentioned_page_parent = self.mentioned_page.parent
        # This should be the same page that houses the original mention.
        self.mentioned_page_parent_parent = self.mentioned_page_parent.parent
        return (
            self.mentioned_page_parent is not None
            and self.mentioned_page_parent_parent is not None
        )

    def _references_correct(self):
        return self._get_mention() and self._get_parents()

    def _is_footnote(self):
        # Check that the footnote parent is a DB with the "Footnotes" suffix in the title.
        if isinstance(
            self.mentioned_page_parent, Database
        ) and self.mentioned_page_parent.title.to_plain_text().endswith("Footnotes"):
            # Raise an exception if the footnotes DB is not a child of the original page.
            # I.e., it's a valid Footnotes DB but not a child (inline) with the original page.
            # This could occur if the user referenced a Footnotes DB on a different page, which
            # we explicitly do not support.
            if (
                not self.mentioned_page_parent_parent.notion_data["id"]
                == self.block.page.notion_data["id"]
            ):
                try:
                    footnote_identifier = (
                        f"title: {self.mentioned_page.title.to_plain_text()}"
                    )
                except AttributeError:
                    footnote_identifier = f"id: {self.mentioned_page.notion_data['id']}"

                raise PluginError(
                    f"Using plugin `{plugin_data_key}`: "
                    f"For footnote ({footnote_identifier}) mention "
                    f"on page: {self.block.page.notion_data['url']}, "
                    "the associated footnotes DB "
                    f"({self.mentioned_page_parent.notion_data['url']}) "
                    "is not a child of the original page"
                )
            return True
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

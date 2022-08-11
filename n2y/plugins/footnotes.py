import re
import logging

from pandoc.types import Note, Str, Para

from n2y.rich_text import TextRichText
from n2y.blocks import ParagraphBlock
from n2y.errors import UseNextClass


plugin_data_key = "n2y.plugins.footnotes"

logger = logging.getLogger(__name__)


class ParagraphWithFootnoteBlock(ParagraphBlock):
    def __init__(self, client, notion_data, page, get_children=True):
        super().__init__(client, notion_data, page, get_children)
        if self._is_footnote():
            self._attach_footnote_data()
        else:
            raise UseNextClass()

    def to_pandoc(self):
        return None

    def _attach_footnote_data(self):
        if plugin_data_key not in self.page.plugin_data:
            self.page.plugin_data[plugin_data_key] = {}
        if self._footnote() not in self.page.plugin_data[plugin_data_key]:
            self.page.plugin_data[plugin_data_key][self._footnote()] = self._footnote_ast()
            if self._footnote_empty():
                msg = 'Empty footnote "[%s]" (%s)'
                logger.warning(msg, self._footnote(), self.notion_url)
        else:
            msg = 'Multiple footnotes for "[%s]", skipping latest (%s)'
            logger.warning(msg, self._footnote(), self.notion_url)

    def _is_footnote(self):
        return self._footnote() is not None

    def _footnote(self):
        first_str = self.rich_text.to_plain_text().split(" ")[0]
        footnotes = re.findall(r"\[(\d+)\]:", first_str)
        if len(footnotes) != 1:
            return None
        return footnotes[0]

    def _footnote_ast(self):
        ast = super().to_pandoc()
        if isinstance(ast, list):
            first_paragraph_footnote_stripped = Para(ast[0][0][2:])
            remaining_paragraphs = ast[1:]
            return [first_paragraph_footnote_stripped] + remaining_paragraphs
        else:
            paragraph_footnote_stripped = Para(ast[0][2:])
            return paragraph_footnote_stripped

    def _footnote_empty(self):
        return len(self.rich_text.to_plain_text()) == 0


class TextRichTextWithFootnoteRef(TextRichText):
    def __init__(self, client, notion_data, block=None):
        super().__init__(client, notion_data, block)
        if not self._is_footnote():
            raise UseNextClass()

    def to_pandoc(self):
        pandoc_ast = []
        for token in super().to_pandoc():
            ref = self._footnote_from_token(token)
            if ref is None:
                pandoc_ast.append(token)
                continue
            if ref not in self.block.page.plugin_data[plugin_data_key]:
                pandoc_ast.append(token)
                msg = 'Missing footnote "[%s]". Rendering as plain text (%s)'
                logger.warning(msg, ref, self.block.notion_url)
                continue
            self._append_footnote_to_ast(pandoc_ast, token, ref)
        return pandoc_ast

    def _append_footnote_to_ast(self, pandoc_ast, token, ref):
        block = self.block.page.plugin_data[plugin_data_key][ref]
        footnote = Note(block) if isinstance(block, list) else Note([block])
        prefix, suffix = token[0].split(f"[^{ref}]")
        pandoc_ast.append(Str(prefix))
        pandoc_ast.append(footnote)
        pandoc_ast.append(Str(suffix))

    def _is_footnote(self):
        return any(self._footnote_from_token(t) is not None for t in super().to_pandoc())

    def _footnote_from_token(self, token):
        if not isinstance(token, Str):
            return None
        refs = re.findall(r"\[\^(\d+)\]", token[0])
        if len(refs) != 1:
            return None
        return refs[0]


notion_classes = {
    "blocks": {"paragraph": ParagraphWithFootnoteBlock},
    "rich_texts": {"text": TextRichTextWithFootnoteRef},
}

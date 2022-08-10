import re

from pandoc.types import Note, Str, Para

from n2y.rich_text import TextRichText
from n2y.blocks import ParagraphBlock


class ParagraphWithFootnoteBlock(ParagraphBlock):
    def __init__(self, client, notion_data, page, get_children=True):
        super().__init__(client, notion_data, page, get_children)
        self._attach_footnote_data_if_exists()

    def to_pandoc(self):
        return None if self._is_footnote() else super().to_pandoc()

    def _attach_footnote_data_if_exists(self):
        if self._is_footnote():
            if "footnotes" not in self.client.plugin_data:
                self.client.plugin_data["footnotes"] = {}
            self.client.plugin_data["footnotes"][self._footnote()] = self._footnote_ast()

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
        return Para(ast[0][2:]) if not isinstance(ast, list) else [Para(ast[0][0][2:])] + ast[1:]


class TextRichTextWithFootnoteRef(TextRichText):
    def to_pandoc(self):
        pandoc_ast = []
        for token in super().to_pandoc():
            if not isinstance(token, Str):
                pandoc_ast.append(token)
                continue
            refs = re.findall(r"\[\^(\d+)\]", token[0])
            if len(refs) != 1:
                pandoc_ast.append(token)
                continue
            block = self.client.plugin_data["footnotes"][refs[0]]
            footnote = Note(block) if isinstance(block, list) else Note([block])
            pandoc_ast.append(footnote)
        return pandoc_ast


notion_classes = {
    "blocks": {"paragraph": ParagraphWithFootnoteBlock},
    "rich_texts": {"text": TextRichTextWithFootnoteRef},
}

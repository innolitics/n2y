import re
from collections import deque

from pandoc.types import Str, Space, SoftBreak, Strong, Emph, Strikeout, Code, Link, \
    Underline, Math, InlineMath

from n2y.property_values import simplify_date


class RichText:
    def __init__(self, client, notion_data):
        self.client = client

        self.plain_text = notion_data['plain_text']
        self.href = notion_data.get('href', None)
        self.notion_type = notion_data['type']

        annotations = notion_data['annotations']
        self.bold = annotations["bold"]
        self.italic = annotations["italic"]
        self.strikethrough = annotations["strikethrough"]
        self.underline = annotations["underline"]
        self.code = annotations["code"]
        self.color = annotations["color"]

    def to_pandoc(self):
        raise NotImplementedError()

    def to_markdown(self):
        return pandoc_ast_to_markdown(self.to_pandoc()).strip('\n')

    def _listify(self, obj):
        return obj if type(obj) == list else [obj]

    def plain_text_to_pandoc(self):
        ast = []
        match = re.findall(r"( +)|(\S+)|(\n+)|(\t+)", self.plain_text)

        for m in match:
            space, word, newline, tab = m
            for _ in range(len(space)):
                ast.append(Space())
            if word:
                ast.append(Str(word))
            for _ in range(len(newline)):
                ast.append(SoftBreak())
            for _ in range(len(tab) * 4):  # 4 spaces per tab
                ast.append(Space())
        return ast

    def annotate_pandoc_ast(self, target):
        # TODO: handle a space that has styling
        prependages = deque()
        appendages = deque()
        problematic_annotations = [
            self.bold, self.italic, self.strikethrough
        ]

        if True in problematic_annotations:
            blank_space = [Space(), SoftBreak()]
            while target[0] in blank_space:
                prependages.append(target.pop(0))
            while target[-1] in blank_space:
                appendages.appendleft(target.pop(-1))

        result = target
        if self.code:
            result = self._listify(Code(("", [], []), result))
        if self.bold:
            result = self._listify(Strong(result))
        if self.italic:
            result = self._listify(Emph(result))
        if self.underline:
            result = self._listify(Underline(result))
        if self.strikethrough:
            result = self._listify(Strikeout(result))

        return list(prependages) + result + list(appendages)


class MentionRichText(RichText):
    def __init__(self, client, notion_data):
        super().__init__(client, notion_data)
        self.mention = client.wrap_notion_mention(notion_data['mention'])

    def to_pandoc(self):
        # TODO: consider handling annotations with styling

        # TODO: use the mention object
        return super().to_pandoc()


class EquationRichText(RichText):
    def __init__(self, client, notion_data):
        super().__init__(client, notion_data)
        self.expression = notion_data['equation']['expression']

    def to_pandoc(self):
        # TODO: consider handling equations with annotatios (e.g., a bolded
        # equation; it seems Notion supports this)
        return [Math(InlineMath(), self.expression)]


class TextRichText(RichText):
    def __init__(self, client, notion_data):
        super().__init__(client, notion_data)

    def to_pandoc(self):
        plain_text_ast = self.plain_text_to_pandoc()
        annotated_ast = self.annotate_pandoc_ast(plain_text_ast)
        if self.href:
            return [Link(
                ('', [], []),
                annotated_ast,
                (self.href, '')
            )]
        else:
            return annotated_ast


DEFAULT_RICH_TEXTS = {
    "text": TextRichText,
    "equation": EquationRichText,
    "mention": MentionRichText,
}


class RichTextArray:
    def __init__(self, client, notion_data):
        self.client = client
        assert isinstance(notion_data, list)
        self.items = [client.wrap_notion_rich_text(i) for i in notion_data]

    def to_pandoc(self):
        return sum([item.to_pandoc() for item in self.items], [])

    def to_markdown(self):
        return pandoc_ast_to_markdown(self.to_pandoc()).strip('\n')

    def to_plain_text(self):
        return ''.join(item.plain_text for item in self.items)

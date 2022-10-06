import re
import logging
from collections import deque

from pandoc.types import (
    Str, Space, LineBreak, Strong, Emph, Strikeout, Code, Link,
    Underline, Math, InlineMath
)

from n2y.utils import pandoc_ast_to_markdown
from n2y.notion_mocks import mock_rich_text


logger = logging.getLogger(__name__)


class RichText:
    """
    A sequence of text that contains the same styling throughout. It also may
    contain an @-mention or an equation (both of which may be styled as well).

    Contains a reference to the block that the rich text is contained in, if
    any. If the block reference is None, then the rich text is perhaps used in
    a property_value or somewhere else.
    """

    def __init__(self, client, notion_data, block=None):
        self.client = client
        self.block = block

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

    @classmethod
    def plain_text_to_pandoc(klass, plain_text):
        ast = []
        match = re.findall(r"( +)|(\xa0+)|(\S+)|(\n+)|(\t+)", plain_text)

        for m in match:
            space, non_breaking_space, word, newline, tab = m
            for _ in range(len(space)):
                ast.append(Space())
            for _ in range(len(non_breaking_space)):
                ast.append(Space())
            if word:
                ast.append(Str(word))
            for _ in range(len(newline)):
                ast.append(LineBreak())
            for _ in range(len(tab) * 4):  # 4 spaces per tab
                ast.append(Space())
        return ast

    def annotate_pandoc_ast(self, target):
        """
        Pandoc's Strong, Emph, Underline, and Strikeout all accept sub-trees of
        inlines. Code does not. This is likely because `a *bold* word` does not
        create a bold word, but *a `code` word* does produce a bolded code word.
        Thus, it's not generally feasible for `annotate_pandoc_ast` to properly
        wrap any ast in a `Code`. If `Code` formatting is to be preserved, then
        the subclasses of `RichText` must apply it separately.
        """
        blank_space = [Space(), LineBreak()]

        if all(n in blank_space for n in target):
            return target

        prependages = deque()
        appendages = deque()
        problematic_annotations = [
            self.bold, self.italic, self.strikethrough
        ]

        # Notion's data model allows space to be bolded, italicized, or
        # strick through, but markdown's doesn't. Thus, since these annotations
        # aren't visible around blank space anyway, we don't apply the
        # annotation to the blank space
        if any(problematic_annotations):
            while target[0] in blank_space:
                prependages.append(target.pop(0))
            while target[-1] in blank_space:
                appendages.appendleft(target.pop(-1))

        result = target
        if self.bold:
            result = [Strong(result)]
        if self.italic:
            result = [Emph(result)]
        if self.underline:
            result = [Underline(result)]
        if self.strikethrough:
            result = [Strikeout(result)]

        return list(prependages) + result + list(appendages)


class MentionRichText(RichText):
    def __init__(self, client, notion_data, block=None):
        super().__init__(client, notion_data, block)
        self.mention = client.wrap_notion_mention(
            notion_data['mention'], notion_data["plain_text"], block,
        )

    def to_pandoc(self):
        if self.code:
            logger.warning('Code formatting is being dropped on mention "%s"', self.plain_text)
        mention_ast = self.mention.to_pandoc()
        return self.annotate_pandoc_ast(mention_ast)


class EquationRichText(RichText):
    def __init__(self, client, notion_data, block=None):
        super().__init__(client, notion_data, block)
        self.expression = notion_data['equation']['expression']

    def to_pandoc(self):
        if self.code:
            logger.warning('Code formatting is being dropped on equation "%s"', self.expression)
        equation_ast = [Math(InlineMath(), self.expression)]
        return self.annotate_pandoc_ast(equation_ast)


class TextRichText(RichText):
    @classmethod
    def from_plain_text(klass, client, string, block=None):
        notion_data = mock_rich_text(string)
        return klass(client, notion_data, block)

    def __init__(self, client, notion_data, block=None):
        super().__init__(client, notion_data, block)

    def to_pandoc(self):
        if not self.code:
            plain_text_ast = self.plain_text_to_pandoc(self.plain_text)
            annotated_ast = self.annotate_pandoc_ast(plain_text_ast)
        else:
            code_ast = [Code(("", [], []), self.plain_text)]
            annotated_ast = self.annotate_pandoc_ast(code_ast)

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
    """
    Contains a sequence or styled text.

    For example, the sentence with a single bolded word

        "The man ran to *eat* the hot dog."

    would be represented as a `RichTextArray` with three elements. The first
    would contain "The man ran to ", the second would contain "eat", and would
    be bolded, and the third would contain " the hot dog.".
    """

    def __init__(self, client, notion_data, block=None):
        self.client = client
        self.block = block

        assert isinstance(notion_data, list)
        self.items = [client.wrap_notion_rich_text(i, block) for i in notion_data]

    def __len__(self):
        return len(self.items)

    def __iter__(self):
        return iter(self.items)

    def __getitem__(self, index):
        return self.items[index]

    def to_pandoc(self):
        return sum([item.to_pandoc() for item in self.items], [])

    def to_markdown(self):
        return pandoc_ast_to_markdown(self.to_pandoc()).strip('\n')

    def to_plain_text(self):
        return ''.join(item.plain_text for item in self.items)

    def matches(self, regexp):
        if len(self.items) > 0:
            first_item = self.items[0]

            # don't match EquationRichText or MentionRichText
            if isinstance(first_item, TextRichText):
                return regexp.match(first_item.plain_text)

    def lstrip(self, string):
        if len(self.items) > 0:
            first_item = self.items[0]
            if isinstance(first_item, TextRichText):
                string_len = len(string)
                if first_item.plain_text[:string_len] == string:
                    self.items[0].plain_text = first_item.plain_text[string_len:]
                    if self.items[0].plain_text == "":
                        self.items.pop(0)

    def prepend(self, string):
        if len(self.items) > 0:
            self.items[0].plain_text = string + self.items[0].plain_text
        else:
            rich_text = TextRichText.from_plain_text(self.client, string)
            self.items.append(rich_text)


class InlineToRichText:
    def __init__(self, pandoc_text):
        self.annotation_types = {
            Strong: "bold",
            Emph: "italic",
            Strikeout: "strikethrough",
            Underline: "underline",
            Code: "code"
        }
        self.text_types = {
            Space: " ",
            LineBreak: "\n",
            Str: self._first_pandoc_arg
        }
        self.rich_text_array = []
        self.annotated_text = ""
        self.current_rich_text = self._new_rich_text
        self._parse_rich_text(pandoc_text)

    @property
    def _new_rich_text(self):
        return {
            "type": None,
            "annotations": [],
            "plain_text": "",
            "href": None
        }

    def _first_pandoc_arg(self, pandoc):
        return pandoc.__dict__["_args"][0]

    def _type_is_text(self):
        if "text" not in self.current_rich_text:
            self.current_rich_text["type"] = "text"
            self.current_rich_text["text"] = {"content": "", "link": None}

    def _store_rich_text(self):
        if self.current_rich_text != self._new_rich_text:
            self.rich_text_array.append(self.current_rich_text)
            self.current_rich_text = self._new_rich_text

    def _parse_rich_text(self, pandoc_text):
        for i, pandoc in enumerate(pandoc_text, 1):
            pandoc_type = type(pandoc)
            if pandoc_type in self.annotation_types:
                self._process_pandoc_annotations(pandoc_type, pandoc)
            elif pandoc_type == Link:
                raise NotImplementedError("Link type text is not yet supported")
            elif pandoc_type == Math:
                raise NotImplementedError("Math type text is not yet supported")
            elif pandoc_type == InlineMath:
                raise NotImplementedError("InlineMath type text is not yet supported")
            elif pandoc_type in self.text_types:
                self._process_pandoc_text(pandoc_type, pandoc)
            if i == len(pandoc_text):
                self._store_rich_text()

    def _process_pandoc_annotations(self, pandoc_type, pandoc):
        self._store_rich_text()
        self._type_is_text()
        arguments = pandoc.__dict__["_args"]
        if pandoc_type == Code:
            text = arguments[1]
            self.current_rich_text["text"]["content"] += text
            self.current_rich_text["plain_text"] += text
        else:
            self._iterate_over_further_annotations(arguments[0])
            self.current_rich_text["text"]["content"] += self.annotated_text
            self.current_rich_text["plain_text"] += self.annotated_text
            self.annotated_text = ""
        self.current_rich_text["annotations"].append(self.annotation_types[pandoc_type])
        self._store_rich_text()

    def _iterate_over_further_annotations(self, pandoc_text):
        for pandoc in pandoc_text:
            pandoc_type = type(pandoc)
            if pandoc_type == Code:
                self.current_rich_text["annotations"].append("code")
                self.annotated_text += pandoc.__dict__["_args"][1]
            elif pandoc_type in self.text_types:
                if pandoc_type == Str:
                    self.annotated_text += self.text_types[Str](pandoc)
                else:
                    self.annotated_text += self.text_types[pandoc_type]
            else:
                self.current_rich_text["annotations"].append(self.annotation_types[pandoc_type])
                self._iterate_over_further_annotations(self._first_pandoc_arg(pandoc))

    def _process_pandoc_text(self, pandoc_type, pandoc):
        self._type_is_text()
        if pandoc_type == Str:
            self.current_rich_text["text"]["content"] += self.text_types[Str](pandoc)
            self.current_rich_text["plain_text"] += self.text_types[Str](pandoc)
        else:
            self.current_rich_text["text"]["content"] += self.text_types[pandoc_type]
            self.current_rich_text["plain_text"] += self.text_types[pandoc_type]

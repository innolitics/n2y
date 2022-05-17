import re
from collections import deque

from pandoc.types import Str, Space, SoftBreak, Strong, Emph, Strikeout, Code, Link, \
    Underline, Math, InlineMath

from n2y.property_values import simplify_date


class PlainText():
    def __init__(self, text):
        self.text = text

    def to_pandoc(self):
        """Tokenize the text"""
        ast = []
        match = re.findall(r"( +)|(\S+)|(\n+)|(\t+)", self.text)

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


class Annotations():
    def __init__(self, block):
        for key, value in block.items():
            self.__dict__[key] = value

    def listify(self, obj):
        return obj if type(obj) == list else [obj]

    def apply_pandoc(self, target):
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
            result = self.listify(Code(("", [], []), result))
        if self.bold:
            result = self.listify(Strong(result))
        if self.italic:
            result = self.listify(Emph(result))
        if self.underline:
            result = self.listify(Underline(result))
        if self.strikethrough:
            result = self.listify(Strikeout(result))

        return list(prependages) + result + list(appendages)


class InlineEquation():
    def __init__(self, block):
        for key, value in block.items():
            self.__dict__[key] = value

    def to_pandoc(self):
        return [Math(InlineMath(), self.expression)]


class Mention():
    """
    Just display the name of the mentions; one can imagine various other ways
    one may want to display these; e.g., using links.
    """

    def __init__(self, block):
        for key, value in block.items():
            self.__dict__[key] = value

    def to_pandoc(self):
        if self.type == 'user':
            return [Str(self.user["name"])]
        if self.type == 'page':
            # TODO: at least replace with the page title
            # TODO: incorporate when implementing https://github.com/innolitics/n2y/issues/24
            page_id = self.page['id']
            return [Str(f'Link to page "{page_id}"')]
        if self.type == 'database':
            # TODO: at least replace with the database title
            # TODO: incorporate when implementing https://github.com/innolitics/n2y/issues/24
            database_id = self.database['id']
            return [Str(f'Link to database "{database_id}"')]
        if self.type == 'date':
            return [Str(simplify_date(self.date))]
        if self.type == 'link_preview':
            return [Link(
                ('', [], []),
                self.plain_text.to_pandoc(),
                (self.href, ''))]
        else:
            raise NotImplementedError(f'Unknown mention type: "{self.type}"')


class RichText():
    def __init__(self, block):
        handlers = {
            'annotations': Annotations,
            'plain_text': PlainText,
            'equation': InlineEquation,
            'mention': Mention,
        }
        # TODO: Replace this loop with explicit attribute setters
        for key, value in block.items():
            if key in handlers.keys():
                self.__dict__[key] = handlers[key](value)
            else:
                self.__dict__[key] = value

    def to_pandoc(self):
        if self.type == 'text':
            if self.annotations.code:
                # Send raw text if it's code.
                return self.annotations.apply_pandoc(self.plain_text.text)
            elif 'href' in self.__dict__ and self.href:
                # links
                return [Link(
                    ('', [], []),
                    self.annotations.apply_pandoc(self.plain_text.to_pandoc()),
                    (self.href, ''))]
            else:
                # regular text
                return self.annotations.apply_pandoc(self.plain_text.to_pandoc())
        elif self.type == 'equation':
            return self.equation.to_pandoc()
        elif self.type == 'mention':
            return self.mention.to_pandoc()
        else:
            raise NotImplementedError(f'Unknown rich text object type: "{self.type}"')


class RichTextArray:
    def __init__(self, text):
        self.items = [RichText(i) for i in text]

    def to_pandoc(self):
        return sum([item.to_pandoc() for item in self.items], [])

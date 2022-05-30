import re
from collections import deque

from pandoc.types import (
    Str, Space, SoftBreak, Strong, Emph, Strikeout, Code, Link, Underline, Math,
    InlineMath
)

from n2y.utils import pandoc_ast_to_markdown


class PlainText:
    def __init__(self, client, text):
        self.client = client
        self.text = text

    def to_pandoc(self):
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


class Annotations:
    def __init__(self, client, block):
        self.client = client
        # TODO: replace with explicit attribute setters
        for key, value in block.items():
            self.__dict__[key] = value

    def listify(self, obj):
        return obj if type(obj) == list else [obj]

    def to_pandoc(self, target):
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


class InlineEquation:
    def __init__(self, client, notion_data):
        self.client = client
        self.expression = notion_data['expression']

    def to_pandoc(self):
        return [Math(InlineMath(), self.expression)]


# TODO: figure out where to put this once the property_values classes are done
# probably shoudl use a client.wrap_property_value method to avoid the circular import
def simplify_date(data):
    if data is None:
        return None
    if data["end"] is None:
        return data["start"]
    else:
        return f'{data["start"]} to {data["end"]}'


class Mention:
    """
    Just display the name of the mentions; one can imagine various other ways
    one may want to display these; e.g., using links.
    """

    def __init__(self, client, block):
        self.client = client
        # TODO: replace this list with explicit property setters
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
                (self.href, '')
            )]
        else:
            raise NotImplementedError(f'Unknown mention type: "{self.type}"')


class RichText():
    def __init__(self, client, notion_data):
        self.client = client
        self.plain_text = PlainText(client, notion_data['plain_text'])
        self.href = notion_data.get('href', None)
        self.annotations = Annotations(client, notion_data['annotations'])
        self.notion_type = notion_data['type']
        if self.notion_type == 'text':
            # we don't use the text object right now since all of the data in it
            # appears to be present in the top-level notion data anyway
            pass
        elif self.notion_type == 'equation':
            self.equation = InlineEquation(client, notion_data['equation'])
        elif self.notion_type == 'mention':
            self.mention = Mention(client, notion_data['mention'])

    def to_pandoc(self):
        # TODO: look into applying annotations to equation or mention types (is
        # that even a possible combination)?
        if self.notion_type == 'text':
            if self.annotations.code:
                return self.annotations.to_pandoc(self.plain_text.text)
            elif self.href:
                return [Link(
                    ('', [], []),
                    self.annotations.to_pandoc(self.plain_text.to_pandoc()),
                    (self.href, ''))]
            else:
                return self.annotations.to_pandoc(self.plain_text.to_pandoc())
        elif self.notion_type == 'equation':
            return self.equation.to_pandoc()
        elif self.notion_type == 'mention':
            return self.mention.to_pandoc()
        else:
            raise NotImplementedError(f'Unknown rich text object type: "{self.notion_type}"')

    def to_markdown(self):
        return pandoc_ast_to_markdown(self.to_pandoc()).strip('\n')


class RichTextArray:
    def __init__(self, client, notion_data):
        self.client = client
        assert isinstance(notion_data, list)
        self.items = [RichText(client, i) for i in notion_data]

    def to_pandoc(self):
        return sum([item.to_pandoc() for item in self.items], [])

    def to_markdown(self):
        return pandoc_ast_to_markdown(self.to_pandoc()).strip('\n')

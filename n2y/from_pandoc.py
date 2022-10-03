from n2y.blocks import ChildPageBlock, ParagraphBlock
from pandoc.types import (
    Str, Para, Pandoc, Link, Math, Strikeout,
    Code, Strong, Emph, Strikeout, Underline,  InlineMath, LineBreak, Space
)

from n2y.notion_mocks import mock_annotations


def process_pandoc_children(arguments, client, page):
    pandoc_children = arguments[-1]
    if type(pandoc_children) != list:
        raise NotImplementedError(
            (
                f"Children are not the last arument for the ",
                "{type(pandoc_ast)} type: arguments - {arguments}"
            )
        )
    class_children = []
    for pandoc_child in pandoc_children:
        class_child = client.instantiate_class(pandoc_child, page)
        class_children.append(class_child)
    return class_children

def process_child_page_pandoc(pandoc_ast, client, page):
    arguments = pandoc_ast.__dict__['_args']
    title = first_pandoc_arg(first_pandoc_arg(arguments[0])["title"])
    mock_notion_data = {
        "title": title
    }
    children = process_pandoc_children(arguments, client, page)
    return mock_notion_data, children

def first_pandoc_arg(pandoc):
    return pandoc.__dict__["_args"][0]

class PandocToRichText():
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
            Str: first_pandoc_arg
        }
        self.rich_text_array = []
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

    def _type_is_text(self):
        if "text" not in self.current_rich_text:
            self.current_rich_text["type"] = "text"
            self.current_rich_text["text"] = {"content": "", "link": None}

    def _store_rich_text(self):
        if self.current_rich_text != self._new_rich_text:
          self.current_rich_text["annotations"] = \
              mock_annotations(self.current_rich_text["annotations"])
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
            if i == len(pandoc_text) and self.current_rich_text != self._new_rich_text:
                self._store_rich_text()

    def _process_pandoc_annotations(self, pandoc_type, pandoc):
        self._store_rich_text()
        self._type_is_text()
        arguments = pandoc.__dict__['_args']
        if pandoc_type == Code:
            text = arguments[1]
            self.current_rich_text["text"]["content"] += text
            self.current_rich_text["plain_text"]+= text
        else:
            annotated_rich_text = PandocToRichText(arguments[0]).rich_text_array[0]
            for annotation, bool in annotated_rich_text["annotations"].items():
                if bool != "default" and bool:
                    self.current_rich_text["annotations"].append(annotation)
            annotated_rich_text["annotations"] = [*self.current_rich_text["annotations"]]
            self.current_rich_text = annotated_rich_text
        self.current_rich_text["annotations"].append(self.annotation_types[pandoc_type])
        self._store_rich_text()

    def _process_pandoc_text(self, pandoc_type, pandoc):
        self._type_is_text()
        if pandoc_type == Str:
            self.current_rich_text["text"]["content"] += self.text_types[Str](pandoc)
            self.current_rich_text["plain_text"]+= self.text_types[Str](pandoc)
        else:
            self.current_rich_text["text"]["content"] += self.text_types[pandoc_type]
            self.current_rich_text["plain_text"]+= self.text_types[pandoc_type]


def process_paragraph_pandoc(pandoc_ast, *_):
    arguments = pandoc_ast.__dict__['_args']
    rich_text_array = PandocToRichText(arguments[0]).rich_text_array
    mock_notion_data = {
        "rich_text": rich_text_array
    }
    return mock_notion_data, []


PANDOC_TYPES = {
    "paragraph": {
        "pandoc": [Para],
        "class": ParagraphBlock,
        "parse_pandoc": process_paragraph_pandoc,
    },
    "child_page": {
        "pandoc": [Pandoc],
        "class": ChildPageBlock,
        "parse_pandoc": process_child_page_pandoc,
    },
}

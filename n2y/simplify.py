"""
Simplify data that has been returned from the Notion API.
"""
import re


def flatten_database_rows(raw_rows):
    return [flatten_database_row(r) for r in raw_rows]


def flatten_database_row(raw_data):
    return {
        simplify_property_name(k): simplify_property(v)
        for k, v in raw_data["properties"].items()
    }


def simplify_property_name(name):
    lower = name.lower().replace(" ", "_")
    return re.sub('[^a-z_0-9]+', '', lower)


def simplify_property(prop):
    if prop["type"] == "rich_text":
        return simplify_rich_text(prop["rich_text"])
    elif prop["type"] == "select":
        return simplify_select(prop["select"])
    elif prop["type"] == "title":
        return simplify_title(prop["title"])
    else:
        # TODO: add other column types
        raise NotImplementedError()


def simplify_select(data):
    return data["name"]


def simplify_title(data):
    return data[0]["plain_text"]


def simplify_rich_text(data):
    # TODO: support formatting that markdown supports (bold, italics,
    # strikeout, links, etc.). Note that this will strip out some things that
    # markdown doesn't support, like colors and underline.
    if len(data) == 0:
        return ""
    else:
        return data[0]["plain_text"]

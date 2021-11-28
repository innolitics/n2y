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
    if prop["type"] == "title":
        return simplify_title(prop["title"])
    elif prop["type"] == "rich_text":
        return simplify_rich_text(prop["rich_text"])
    elif prop["type"] == "select":
        return simplify_select(prop["select"])
    elif prop["type"] == "people":
        return simplify_people(prop["people"])
    elif prop["type"] == "url":
        return prop["url"]
    elif prop["type"] == "number":
        return prop["number"]
    elif prop["type"] == "email":
        return prop["email"]
    elif prop["type"] == "checkbox":
        return prop["checkbox"]
    elif prop["type"] == "phone_number":
        return prop["phone_number"]
    elif prop["type"] == "date":
        return simplify_date(prop["date"])
    else:
        # TODO: add remaining column types
        raise NotImplementedError()


def simplify_title(data):
    return data[0]["plain_text"]


def simplify_select(data):
    return data["name"]


def simplify_rich_text(data):
    # TODO: support formatting that markdown supports (bold, italics,
    # strikeout, links, etc.). Note that this will strip out some things that
    # markdown doesn't support, like colors and underline.
    if len(data) == 0:
        return ""
    else:
        return data[0]["plain_text"]


def simplify_people(data):
    return [p["name"] for p in data]


def simplify_date(data):
    if data["end"] is None:
        return data["start"]
    else:
        return f'{data["start"]} to {data["end"]}'

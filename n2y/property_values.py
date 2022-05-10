"""
Simplify data that has been returned from the Notion API.
"""
import logging

logger = logging.getLogger(__name__)


def flatten_database_rows(raw_rows):
    return [flatten_property_values(r) for r in raw_rows]


def flatten_property_values(raw_data):
    return {
        k: simplify_property(v)
        for k, v in raw_data["properties"].items()
    }


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
    elif prop["type"] == "multi_select":
        return [option["name"] for option in prop["multi_select"]]
    elif prop["type"] == "relation":
        logger.warning("field type 'relation' is not fully implemented")
        return [relation["id"] for relation in prop["relation"]]
    elif prop["type"] == "rollup":
        logger.warning("field type 'rollup' is not fully implemented")
        r = prop["rollup"]
        return {"type": r["type"], "function": r["function"], r["type"]: r[r["type"]]}
    elif prop["type"] == "formula":
        logger.warning("field type 'formula' is not fully implemented")
        return prop["formula"]["string"]
    elif prop["type"] == "files":
        logger.warning("field type 'files' is not fully implemented")
        return prop["files"]
    else:
        # TODO: add remaining column types
        raise NotImplementedError()


def simplify_title(data):
    if data is None or len(data) == 0:
        return None
    return data[0]["plain_text"]


def simplify_select(data):
    if data is None:
        return None
    return data["name"]


def simplify_rich_text(data):
    # Note that this will strip out some things that markdown doesn't support,
    # like colors and underlines.
    return "".join(simplify_rich_text_item(r) for r in data)


def simplify_rich_text_item(data):
    text = escape_markdown(data["plain_text"])
    if data["annotations"]["code"]:
        text = f"`{text}`"
    if data["annotations"]["bold"]:
        text = f"**{text}**"
    if data["annotations"]["italic"]:
        text = f"*{text}*"
    if data["annotations"]["strikethrough"]:
        text = f"~~{text}~~"
    if data["href"] is not None:
        text = f"[{text}]({data['href']})"
    return text


def escape_markdown(text):
    # TODO: think through other things we should escape and if/when we need to
    # escape
    escaped = "*_`[]"
    return "".join(c if c not in escaped else f"\\{c}" for c in text)


def simplify_people(data):
    return [p["name"] for p in data]


def simplify_date(data):
    if data is None:
        return None
    if data["end"] is None:
        return data["start"]
    else:
        return f'{data["start"]} to {data["end"]}'

from pandoc.types import Str, Para, Plain, Space, Header, Strong, Emph, Strikeout,\
    Code, BulletList, OrderedList, Decimal, Period, Meta, Pandoc, Link, HorizontalRule, CodeBlock, \
    BlockQuote
import re

# Notes:
# A single Notion block may have multiple lines of text.
# A page is a block that puts children into "content" attribute.
# We transform page block to resemble other block types.
#
# Pandoc makes each word a block, and spaces are blocks too!
#
# Block types used here that do not exist in Notion:
#   container - block with no top-level content, only children (used to parse a page and lists)
#   bulleted_list - Notion has bulleted_list_item, but no enclosing container
#   numbered_list - Notion has numbered_list_item, but no enclusing container


def convert(input_page):
    ast = _parse_block({"type": "container",
                        "has_children": True,
                        "children": input_page["content"]})
    doc = Pandoc(Meta({}), ast)
    return doc


def _parse_block(block):
    ast = []
    if block["type"] in ["container"]:
        # do nothing since there a no blocks at this level, only children
        pass
    elif block["type"] == "paragraph":
        ast.append(_parse_paragraph(block))

    elif block["type"] == "heading_1":
        ast.append(_parse_heading_1(block))
    elif block["type"] == "heading_2":
        ast.append(_parse_heading_2(block))
    elif block["type"] == "heading_3":
        ast.append(_parse_heading_3(block))
    elif block["type"] == "bulleted_list":
        ast.append(_parse_bulleted_list(block))
    elif block["type"] == "numbered_list":
        ast.append(_parse_numbered_list(block))
    elif block["type"] == "bookmark":
        ast.append(_parse_bookmark(block))
    elif block["type"] == "divider":
        ast.append(HorizontalRule())
    elif block["type"] == "code":
        ast.append(_parse_code_block(block))
    elif block["type"] == "quote":
        ast.append(_parse_block_quote(block))
    else:
        # TODO: add remaining block types
        raise NotImplementedError(f"Unknown block type {block['type']}")

    if block["has_children"]:
        previous_child_type = ""
        list_accumulator = []
        for child in block["children"]:
            ########################
            # handle bulleted list #
            ########################
            if child["type"] == "bulleted_list_item" \
                    and previous_child_type != "bulleted_list_item":
                # handle leftovers from a pervious list if it exists
                if len(list_accumulator):
                    if previous_child_type == "numbered_list_item":
                        ast.extend(_parse_block({"type": "numbered_list",
                                                "has_children": False, "items": list_accumulator}))
                    else:
                        raise ValueError
                # starting a new list
                list_accumulator = [child]
            elif child["type"] == "bulleted_list_item" \
                    and previous_child_type == "bulleted_list_item":
                # append list
                list_accumulator.append(child)
            elif child["type"] != "bulleted_list_item" \
                    and previous_child_type == "bulleted_list_item":
                # create bulleted list container and append it to ast
                ast.extend(_parse_block({"type": "bulleted_list",
                                        "has_children": False, "items": list_accumulator}))
                # empty the accumulator
                list_accumulator = []
                if child["type"] == "numbered_list_item":
                    # starting a new list
                    list_accumulator = [child]
                else:
                    ast.extend(_parse_block(child))

            ########################
            # handle numbered list #
            ########################
            elif child["type"] == "numbered_list_item" \
                    and previous_child_type != "numbered_list_item":
                # starting a new list
                list_accumulator = [child]
            elif child["type"] == "numbered_list_item" \
                    and previous_child_type == "numbered_list_item":
                # append list
                list_accumulator.append(child)
            elif child["type"] != "numbered_list_item" \
                    and previous_child_type == "numbered_list_item":
                # create numbered list container and append it to ast
                ast.extend(_parse_block({"type": "numbered_list",
                                        "has_children": False, "items": list_accumulator}))
                # empty the accumulator
                list_accumulator = []
                if child["type"] != "bulleted_list_item":
                    ast.extend(_parse_block(child))

            ####################################
            # handle blocks that are not lists #
            ####################################
            else:
                ast.extend(_parse_block(child))
            previous_child_type = child["type"]

        # handle numbered and bulleted lists that were not followed by another block type
        if len(list_accumulator):
            if previous_child_type == "bulleted_list_item":
                ast.extend(_parse_block({"type": "bulleted_list",
                                        "has_children": False, "items": list_accumulator}))
            elif previous_child_type == "numbered_list_item":
                ast.extend(_parse_block({"type": "numbered_list",
                                        "has_children": False, "items": list_accumulator}))
    return ast


def _parse_plain_text(text):
    """Split into words and spaces"""
    ast = []
    match = re.findall(r"( +)?\b(\S+)+( +)?", text)

    for m in match:
        spaces_before, word, spaces_after = m
        for _ in range(len(spaces_before)):
            ast.append(Space())
        ast.append(Str(word))
        for _ in range(len(spaces_after)):
            ast.append(Space())
    return ast


def _parse_paragraph(block):
    ast = Para(_parse_rich_text_array(block["paragraph"]["text"]))
    return ast


def _parse_rich_text_array(rich_text_array):
    ast = []
    for item in rich_text_array:
        text = _parse_plain_text(item["plain_text"])
        if item["annotations"]["bold"]:
            text = [Strong(text)]
        if item["annotations"]["italic"]:
            text = [Emph(text)]
        # Underline is not supported in markdown.
        # TODO: Enable using command line argument?
        # (in case we are exporting to something other than markdown)
        #
        # if item["annotations"]["underline"]:
        #     text = [Underline(text)]
        if item["annotations"]["strikethrough"]:
            text = [Strikeout(text)]
        if item["annotations"]["code"]:
            text = [Code(("", [], []), item["plain_text"])]
        if item["href"]:
            text = [Link(('', [], []), text, (item["href"], ''))]
        ast.extend(text)
    return ast


def _parse_heading_1(block):
    return Header(1, ("", [], []), _parse_rich_text_array(block["heading_1"]["text"]))


def _parse_heading_2(block):
    return Header(2, ("", [], []), _parse_rich_text_array(block["heading_2"]["text"]))


def _parse_heading_3(block):
    return Header(3, ("", [], []), _parse_rich_text_array(block["heading_3"]["text"]))


def _parse_bulleted_list(block):
    items = []
    for item in block["items"]:
        items.append(_parse_bulleted_list_item(item))
    return BulletList(items)


def _parse_numbered_list(block):
    items = []
    for item in block["items"]:
        items.append(_parse_numbered_list_item(item))
    return OrderedList((1, Decimal(), Period()), items)


def _parse_bulleted_list_item(block):
    result = [Plain(_parse_rich_text_array(block["bulleted_list_item"]["text"]))]
    if block["has_children"]:
        parsed_children = \
            _parse_block({"type": "container", "has_children": True, "children": block["children"]})
        result.extend(parsed_children)
    return result


def _parse_numbered_list_item(block):
    result = [Plain(_parse_rich_text_array(block["numbered_list_item"]["text"]))]
    if block["has_children"]:
        parsed_children = \
            _parse_block({"type": "container", "has_children": True, "children": block["children"]})
        result.extend(parsed_children)
    return result


def _parse_bookmark(block):
    """A bookmark block in Notion is a paragraph with just a link"""
    caption = _parse_rich_text_array(block["bookmark"]["caption"])
    if len(caption) == 0:
        caption = [Str(block["bookmark"]["url"])]
    return Para([Link(('', [], []), caption, (block["bookmark"]["url"], ''))])


def _parse_code_block(block):
    """Handle fenced code"""
    return CodeBlock(('', [block["code"]["language"]], []), block['code']['text'][0]['plain_text'])


def _parse_block_quote(block):
    return BlockQuote([Para(_parse_rich_text_array(block["quote"]["text"]))])

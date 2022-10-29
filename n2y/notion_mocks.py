from datetime import datetime
import uuid

from n2y.utils import strip_hyphens


def mock_id():
    return str(uuid.uuid4())


def mock_user(**kwargs):
    return {'object': 'user', 'id': mock_id(), **kwargs}


def mock_person_user(name, email):
    return mock_user(name=name, type="person", person={"email": email})


def mock_rich_text_array(text_blocks_descriptors):
    if isinstance(text_blocks_descriptors, str):
        return [mock_rich_text(text_blocks_descriptors, [])]
    else:
        return [mock_rich_text(*desc) for desc in text_blocks_descriptors]


def mock_rich_text(text, annotations=None, href=None, mention=None, link=None):
    if annotations is None:
        annotations = []
    if mention is None:
        rich_text_type = 'text'
        content = {'content': text, 'link': link}
    else:
        rich_text_type = 'mention'
        content = mention
    return {
        'type': rich_text_type,
        'annotations': mock_annotations(annotations),
        'plain_text': text,
        'href': href,
        rich_text_type: content,
    }


def mock_annotations(annotations=None):
    if annotations is None:
        annotations = []
    color_string = [a for a in annotations if 'color' in a]
    if color_string:
        color = color_string[0].replace('color:', '')
    else:
        color = 'default'
    return {
        'bold': True if 'bold' in annotations else False,
        'italic': True if 'italic' in annotations else False,
        'strikethrough': True if 'strikethrough' in annotations else False,
        'underline': True if 'underline' in annotations else False,
        'code': True if 'code' in annotations else False,
        'color': color
    }


def mock_user_mention():
    return {
        'type': 'user',
        'user': mock_user(),
    }


def mock_page_mention():
    return {
        'type': 'page',
        'page': {
            'id': mock_id(),
        },
    }


def mock_database_mention():
    return {
        'type': 'database',
        'database': {
            'id': mock_id(),
        },
    }


def mock_block(block_type, content, has_children=False, **kwargs):
    created_by = mock_user()
    created_time = datetime.now().isoformat()
    notion_id = mock_id()
    return {
        'id': notion_id,
        'url': f'#{strip_hyphens(notion_id)}',
        'created_time': created_time,
        'created_by': created_by,
        'last_edited_time': created_time,
        'last_edited_by': created_by,
        'object': 'block',
        'has_children': has_children,
        'archived': False,
        'type': block_type,
        block_type: content,
        **kwargs,
    }


def mock_paragraph_block(text_blocks_descriptors, **kwargs):
    return mock_block('paragraph', {
        'color': 'default',
        'rich_text': mock_rich_text_array(text_blocks_descriptors),
    }, **kwargs)


def mock_file(url):
    return {
        'url': url,
        'expiry_time': None
    }


def mock_property_value(property_value_type, content):
    return {
        'id': mock_id(),
        'type': property_value_type,
        property_value_type: content,
    }


def mock_rich_text_property_value(text_blocks_descriptors):
    return mock_property_value("rich_text", mock_rich_text_array(text_blocks_descriptors))


def mock_formula_property_value(formula_type, content):
    return mock_property_value("formula", {
        "type": formula_type,
        formula_type: content,
    })


def mock_rollup_property_value(rollup_type, content):
    return mock_property_value("rollup", {
        "type": rollup_type,
        "function": "function",
        rollup_type: content,
    })


def mock_select_option(name, **kwargs):
    return {
        'id': mock_id(),
        'name': name,
        'color': 'green',
        **kwargs,
    }


def mock_relation_value():
    return {"id": mock_id()}


def mock_page(title="Mock Page", extra_properties=None):
    if extra_properties is None:
        extra_properties = {}
    user = mock_user()
    created_time = datetime.now().isoformat()
    notion_id = mock_id()
    hyphenated_title = title.replace(" ", "-")
    return {
        'object': 'page',
        'id': notion_id,
        'created_time': created_time,
        'last_edited_time': created_time,
        'created_by': user,
        'last_edited_by': user,
        'cover': None,
        'icon': None,
        'parent': {'type': 'page_id', 'page_id': mock_id()},
        'archived': False,
        'properties': {
            'title': {
                'id': 'title',
                'type': 'title',
                'title': mock_rich_text_array(title)
            }, **extra_properties,
        },
        'url': f'https://www.notion.so/{hyphenated_title}-{notion_id}',
    }


def mock_database(title='Mock Database', extra_properties={}):
    hyphenated_title = title.replace(" ", "-")
    created_time = datetime.now().isoformat()
    notion_id = mock_id()
    user = mock_user()
    return {
        'object': 'database',
        'id': notion_id,
        'cover': None,
        'icon': None,
        'created_time': created_time,
        'last_edited_time': created_time,
        'created_by': user,
        'last_edited_by': user,
        'title': mock_rich_text_array(title),
        'description': [],
        'is_inline': False,
        'archived': False,
        'properties': {
            'Tags': {
                'id': mock_id(),
                'name': 'Tags',
                'type': 'multi_select',
                'multi_select': {'options': []}
            },
            'Number': {
                'id': mock_id(),
                'name': 'Number',
                'type': 'number',
                'number': {'format': 'number'}
            },
            'Name': {
                'id': 'title',
                'name': 'Name',
                'type': 'title',
                'title': {}
            }, **extra_properties,
        },
        'parent': {
            'type': 'page_id',
            'page_id': mock_id()
        },
        'url': f'https://www.notion.so/{hyphenated_title}-{notion_id}',
    }

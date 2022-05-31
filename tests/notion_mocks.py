from datetime import datetime
import uuid


def mock_user(**kwargs):
    return {'object': 'user', 'id': str(uuid.uuid4()), **kwargs}


def mock_person_user(name, email):
    return mock_user(name=name, type="person", person={"email": email})


def mock_annotations(annotations=None):
    if annotations is None:
        annotations = []
    return {
        'bold': True if 'bold' in annotations else False,
        'italic': True if 'italic' in annotations else False,
        'strikethrough': True if 'strikethrough' in annotations else False,
        'underline': True if 'underline' in annotations else False,
        'code': True if 'code' in annotations else False,
        'color': 'default'
    }


def mock_rich_text(text, annotations=None, href=None):
    if annotations is None:
        annotations = []
    return {
        'type': 'text',
        'text': {'content': text, 'link': None},
        'annotations': mock_annotations(annotations),
        'plain_text': text,
        'href': href,
    }


def mock_rich_text_array(text_blocks_descriptors):
    return [mock_rich_text(t, a) for t, a in text_blocks_descriptors]


def mock_block(block_type, content, has_children=False, **kwargs):
    created_by = mock_user()
    created_time = datetime.now().isoformat()
    return {
        'id': str(uuid.uuid4()),
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
        'id': str(uuid.uuid4()),
        'type': property_value_type,
        property_value_type: content,
    }


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
        'id': str(uuid.uuid4()),
        'name': name,
        'color': 'green',
        **kwargs,
    }


def mock_relation_value():
    return {"id": str(uuid.uuid4)}

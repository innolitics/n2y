import yaml

from n2y.property_values import flatten_property_values, simplify_rich_text


def test_flatten_database_rows():
    raw = yaml.safe_load('''
      url:
        type: url
        url: https://example.com
      number:
        number: 7
        type: number
      email:
        email: info@innolitics.com
        type: email
      bool:
        checkbox: false
        type: checkbox
      people:
        people:
        - name: J. David Giese
        type: people
      date:
        date:
          end: null
          start: '2021-11-04'
        type: date
      empty:
        rich_text: []
        type: rich_text
      title:
        id: title
        title:
        - plain_text: 'title'
        type: title
      select:
        select:
          name: partial
        type: select
      phone:
        phone_number: 555-555-5555
        type: phone_number
    ''')
    flattened = {
        "url": "https://example.com",
        "number": 7,
        "email": "info@innolitics.com",
        "bool": False,
        "people": ["J. David Giese"],
        "date": '2021-11-04',
        "empty": '',
        "title": 'title',
        "select": "partial",
        "phone": "555-555-5555",
    }

    assert flatten_property_values(raw) == flattened


def test_simplify_rich_text_escape_specials():
    # we always escape to keep things simple; this may not be desirable
    assert simplify_rich_text([rich("h_")]) == r"h\_"
    assert simplify_rich_text([rich("h`")]) == r"h\`"
    assert simplify_rich_text([rich("h*")]) == r"h\*"
    assert simplify_rich_text([rich("h__")]) == r"h\_\_"


def test_simplify_rich_text_bold():
    assert simplify_rich_text([rich("hello", "b")]) == "**hello**"


def test_simplify_rich_text_bold_italic():
    assert simplify_rich_text([rich("hello", "bi")]) == "***hello***"


def test_simplify_rich_text_bold_italic_code():
    assert simplify_rich_text([rich("hello", "bic")]) == "***`hello`***"


def test_simplify_rich_text_bold_italic_code_strikethrough():
    assert simplify_rich_text([rich("hello", "bics")]) == "~~***`hello`***~~"


def test_simplify_rich_text_bold_then_bold_italic():
    # TODO: ideally this would reduce down to "**x*y***"
    assert simplify_rich_text([rich("x", "b"), rich("y", "bi")]) == "**x*****y***"


def test_simplify_rich_text_link():
    assert simplify_rich_text([rich("hello", href="#")]) == "[hello](#)"


def test_simplify_rich_text_link_with_styling():
    assert simplify_rich_text([rich("hello", "i", "#")]) == "[*hello*](#)"


def rich(text, qualifiers="", href=None):
    return {
        "plain_text": text,
        "annotations": {
            "bold": "b" in qualifiers,
            "code": "c" in qualifiers,
            "italic": "i" in qualifiers,
            "strikethrough": "s" in qualifiers,
        },
        "href": href,
    }

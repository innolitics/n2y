import yaml

from n2y.simplify import flatten_database_row


def test_flatten_database_rows():
    raw = yaml.safe_load('''
    properties:
        rich_text:
          rich_text:
          - plain_text: Rich
          type: rich_text
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
        "rich_text": "Rich",
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

    assert flatten_database_row(raw) == flattened

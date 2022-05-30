from datetime import datetime
import logging

from n2y.utils import fromisoformat


logger = logging.getLogger(__name__)


class PropertyValue:
    def __init__(self, client, notion_data):
        self.client = client
        self.notion_id = notion_data['id']
        self.notion_type = notion_data['type']
        self.notion_data = notion_data

    def to_value(self):
        raise NotImplementedError()


class TitlePropertyValue(PropertyValue):
    def __init__(self, client, notion_data):
        super().__init__(client, notion_data)
        self.text = client.wrap_notion_rich_text_array(notion_data['title'])

    def to_value(self):
        return self.text.to_markdown()


class TextPropertyValue(PropertyValue):
    def __init__(self, client, notion_data):
        super().__init__(client, notion_data)
        self.text = client.wrap_notion_rich_text_array(notion_data['rich_text'])

    def to_value(self):
        return self.text.to_markdown()


class NumberPropertyValue(PropertyValue):
    def __init__(self, client, notion_data):
        super().__init__(client, notion_data)
        self.number = notion_data['number']

    def to_value(self):
        return self.number


class SelectPropertyValue(PropertyValue):
    def __init__(self, client, notion_data):
        super().__init__(client, notion_data)
        notion_select = notion_data['select']
        if notion_select is not None:
            self.notion_option_id = notion_select['id']
            self.name = notion_select['name']
            self.color = notion_select['color']
        else:
            self.notion_option_id = None
            self.name = None
            self.color = None

    def to_value(self):
        # Note: the Notion UI shouldn't allow you to have two options with the
        # same name
        return self.name


class MultiSelectPropertyValue(PropertyValue):
    def __init__(self, client, notion_data):
        super().__init__(client, notion_data)
        self.options = [MultiSelectOption(self.client, no) for no in notion_data['multi_select']]

    def to_value(self):
        # Note: the Notion UI shouldn't allow you to have two options with the
        # same name
        return [o.name for o in self.options]


class MultiSelectOption:
    def __init__(self, client, notion_option):
        self.client = client
        self.notion_id = notion_option['id']
        self.name = notion_option['name']
        self.color = notion_option['color']


def _process_notion_date(notion_date):
    if notion_date is None:
        return None
    elif notion_date.get('end', None):
        return [
            notion_date['start'],
            notion_date['end'],
        ]
    else:
        return notion_date['start']


class DatePropertyValue(PropertyValue):
    def __init__(self, client, notion_data):
        super().__init__(client, notion_data)
        self.value = _process_notion_date(notion_data['date'])

    def to_value(self):
        return self.value


class PeoplePropertyValue(PropertyValue):
    def __init__(self, client, notion_data):
        super().__init__(client, notion_data)
        self.people = [client.wrap_notion_user(nu) for nu in notion_data['people']]

    def to_value(self):
        return [u.to_value() for u in self.people]


class FilesPropertyValue(PropertyValue):
    def __init__(self, client, notion_data):
        super().__init__(client, notion_data)
        self.files = [client.wrap_notion_file(nf) for nf in notion_data['files']]

    def to_value(self):
        return [f.to_value() for f in self.files]


class CheckboxPropertyValue(PropertyValue):
    def __init__(self, client, notion_data):
        super().__init__(client, notion_data)
        self.checkbox = notion_data['checkbox']

    def to_value(self):
        return self.checkbox


class UrlPropertyValue(PropertyValue):
    def __init__(self, client, notion_data):
        super().__init__(client, notion_data)
        self.url = notion_data['url']

    def to_value(self):
        return self.url


class EmailPropertyValue(PropertyValue):
    def __init__(self, client, notion_data):
        super().__init__(client, notion_data)
        self.email = notion_data['email']

    def to_value(self):
        return self.email


class PhoneNumberPropertyValue(PropertyValue):
    def __init__(self, client, notion_data):
        super().__init__(client, notion_data)
        self.phone_number = notion_data['phone_number']

    def to_value(self):
        return self.phone_number


class FormulaPropertyValue(PropertyValue):
    def __init__(self, client, notion_data):
        super().__init__(client, notion_data)
        # TODO: set other attributes
        notion_formula = notion_data["formula"]
        if notion_formula["type"] == "date":
            self.value = _process_notion_date(notion_formula["date"])
        else:
            self.value = notion_formula[notion_formula["type"]]

    def to_value(self):
        return self.value


class RelationPropertyValue(PropertyValue):
    def __init__(self, client, notion_data):
        super().__init__(client, notion_data)
        self.ids = [related["id"] for related in notion_data["relation"]]

    def to_value(self):
        return self.ids


class RollupPropertyValue(PropertyValue):
    def __init__(self, client, notion_data):
        super().__init__(client, notion_data)
        notion_rollup = notion_data["rollup"]
        self.function = notion_rollup["function"]
        if notion_rollup["type"] == "date":
            self.value = _process_notion_date(notion_rollup['date'])
        else:
            self.value = notion_rollup[notion_rollup["type"]]
        # TODO: handle arrays of dates

    def to_value(self):
        return self.value


class CreatedTimePropertyValue(PropertyValue):
    def __init__(self, client, notion_data):
        super().__init__(client, notion_data)
        self.created_time = fromisoformat(notion_data['created_time'])

    def to_value(self):
        return datetime.isoformat(self.created_time)


class CreatedByPropertyValue(PropertyValue):
    def __init__(self, client, notion_data):
        super().__init__(client, notion_data)
        self.created_by = client.wrap_notion_user(notion_data['created_by'])

    def to_value(self):
        return self.created_by.to_value()


class LastEditedTimePropertyValue(PropertyValue):
    def __init__(self, client, notion_data):
        super().__init__(client, notion_data)
        self.last_edited_time = fromisoformat(notion_data['last_edited_time'])

    def to_value(self):
        return datetime.isoformat(self.last_edited_time)


class LastEditedBy(PropertyValue):
    def __init__(self, client, notion_data):
        super().__init__(client, notion_data)
        self.last_edited_by = client.wrap_notion_user(notion_data['last_edited_by'])

    def to_value(self):
        return self.last_edited_by.to_value()


DEFAULT_PROPERTY_VALUES = {
    'title': TitlePropertyValue,
    'rich_text': TextPropertyValue,
    'number': NumberPropertyValue,
    'select': SelectPropertyValue,
    'multi_select': MultiSelectPropertyValue,
    'date': DatePropertyValue,
    'people': PeoplePropertyValue,
    'files': FilesPropertyValue,
    'checkbox': CheckboxPropertyValue,
    'url': UrlPropertyValue,
    'email': EmailPropertyValue,
    'phone_number': PhoneNumberPropertyValue,
    'formula': FormulaPropertyValue,
    'relation': RelationPropertyValue,
    'rollup': RollupPropertyValue,
    'created_time': CreatedTimePropertyValue,
    'created_by': CreatedByPropertyValue,
    'last_edited_time': LastEditedTimePropertyValue,
    'last_edited_by': LastEditedBy,


}

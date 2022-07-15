from datetime import datetime
import logging

from n2y.utils import fromisoformat, process_notion_date, processed_date_to_plain_text


logger = logging.getLogger(__name__)


class PropertyValue:
    def __init__(self, client, notion_data):
        self.client = client
        self.notion_property_id = notion_data.get(
            'id', None)  # will be none for rollup array values
        self.notion_type = notion_data['type']

    def to_value(self):
        raise NotImplementedError()


class TitlePropertyValue(PropertyValue):
    def __init__(self, client, notion_data):
        # TODO: handle the case when there are more than 25 rich text items in the property
        # See https://developers.notion.com/reference/retrieve-a-page-property
        super().__init__(client, notion_data)
        self.rich_text = client.wrap_notion_rich_text_array(notion_data['title'])

    def to_value(self):
        # Notion allows styling of the title, however, in their UI they display
        # the title property without any styling. Thus, if you copy/paste styled
        # text into a title this styling can be hidden and can re-appear after
        # the document conversion. To avoid this surprise, we only generate
        # plain text here.
        return self.rich_text.to_plain_text()


class TextPropertyValue(PropertyValue):
    def __init__(self, client, notion_data):
        # TODO: handle the case when there are more than 25 rich text items in the property
        # See https://developers.notion.com/reference/retrieve-a-page-property
        super().__init__(client, notion_data)
        self.rich_text = client.wrap_notion_rich_text_array(notion_data['rich_text'])

    def to_value(self):
        return self.rich_text.to_markdown()


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


class DatePropertyValue(PropertyValue):
    def __init__(self, client, notion_data):
        # TODO: handle timezones
        super().__init__(client, notion_data)
        self.value = process_notion_date(notion_data['date'])

    def to_value(self):
        return self.value

    def to_plain_text(self):
        return processed_date_to_plain_text(self.value)


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
            self.value = process_notion_date(notion_formula["date"])
        else:
            self.value = notion_formula[notion_formula["type"]]

    def to_value(self):
        return self.value


class RelationPropertyValue(PropertyValue):
    def __init__(self, client, notion_data):
        # TODO: handle the case when there are more than 25 pages in the relation
        # See https://developers.notion.com/reference/retrieve-a-page-property
        super().__init__(client, notion_data)
        self.ids = [related["id"] for related in notion_data["relation"]]

    def to_value(self):
        return self.ids


class RollupPropertyValue(PropertyValue):
    def __init__(self, client, notion_data):
        # TODO: handle the case when the rollup needs to be paginated
        # See https://developers.notion.com/reference/retrieve-a-page-property
        super().__init__(client, notion_data)
        notion_rollup = notion_data["rollup"]
        self.rollup_type = notion_rollup["type"]
        self.function = notion_rollup["function"]
        if self.rollup_type == "date":
            self.value = process_notion_date(notion_rollup['date'])
        elif self.rollup_type == "string":
            self.value = notion_rollup['string']
        elif self.rollup_type == "number":
            self.value = notion_rollup['number']
        elif self.rollup_type == "array":
            self.value = [
                self.client.wrap_notion_property_value(pv)
                for pv in notion_rollup['array']
            ]
        else:
            logger.warning("Unhandled rollup type %s", notion_rollup["type"])
            self.value = notion_rollup[notion_rollup["type"]]
        # TODO: handle arrays of dates

    def to_value(self):
        if self.rollup_type == "date":
            return self.value
        elif self.rollup_type == "string":
            return self.value
        elif self.rollup_type == "number":
            return self.value
        elif self.rollup_type == "array":
            return [pv.to_value() for pv in self.value]
        else:
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

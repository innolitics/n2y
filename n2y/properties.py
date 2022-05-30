class Property:
    def __init__(self, client, notion_data):
        self.client = client
        self.notion_id = notion_data['id']
        self.notion_type = notion_data['type']
        self.name = notion_data['name']


# TODO: eventually add methods for generating SQL type expresions or JSON
# schema from these guys


class TitleProperty(Property):
    pass


class TextProperty(Property):
    pass


class NumberProperty(Property):
    def __init__(self, client, notion_data):
        super().__init__(client, notion_data)
        self.format = notion_data['number']["format"]


class SelectProperty(Property):
    def __init__(self, client, notion_data):
        super().__init__(client, notion_data)
        notion_options = notion_data['select']['options']
        self.options = [SelectOption(self.client, no) for no in notion_options]


class SelectOption:
    def __init__(self, client, notion_option):
        self.client = client
        self.notion_id = notion_option['id']
        self.name = notion_option['name']
        self.color = notion_option['color']


class MultiSelectProperty(Property):
    def __init__(self, client, notion_data):
        super().__init__(client, notion_data)
        notion_options = notion_data['multi_select']['options']
        self.options = [MultiSelectOption(self.client, no) for no in notion_options]


class MultiSelectOption:
    """
    This class appears identical to SelectOption, but the notion API docs calls it a
    separate thing so it appears like it may change in the future; also, it
    seems like one may want a plugin that treats the two types of options
    differently
    """

    def __init__(self, client, notion_option):
        self.client = client
        self.notion_id = notion_option['id']
        self.name = notion_option['name']
        self.color = notion_option['color']


class DateProperty(Property):
    pass


class PeopleProperty(Property):
    pass


class FilesProperty(Property):
    pass


class CheckboxProperty(Property):
    pass


class UrlProperty(Property):
    pass


class EmailProperty(Property):
    pass


class PhoneNumberProperty(Property):
    pass


class FormulaProperty(Property):
    def __init__(self, client, notion_data):
        super().__init__(client, notion_data)
        self.formula = notion_data["formula"]["expression"]


class RelationProperty(Property):
    def __init__(self, client, notion_data):
        super().__init__(client, notion_data)
        relation = notion_data["relation"]
        self.database_id = relation["database_id"]
        self.synced_property_name = relation.get("synced_property_name", None)
        self.synced_property_id = relation.get("synced_property_id", None)


class RollupProperty(Property):
    def __init__(self, client, notion_data):
        super().__init__(client, notion_data)
        rollup = notion_data["rollup"]
        self.relation_property_name = rollup["relation_property_name"]
        self.relation_property_id = rollup["relation_property_id"]
        self.rollup_property_name = rollup["rollup_property_name"]
        self.rollup_property_id = rollup["rollup_property_id"]
        self.function = rollup["function"]


class CreatedTimeProperty(Property):
    pass


class CreatedByProperty(Property):
    pass


class LastEditedTimeProperty(Property):
    pass


class LastEditedBy(Property):
    pass


DEFAULT_PROPERTIES = {
    'title': TitleProperty,
    'rich_text': TextProperty,
    'number': NumberProperty,
    'select': SelectProperty,
    'multi_select': MultiSelectProperty,
    'date': DateProperty,
    'people': PeopleProperty,
    'files': FilesProperty,
    'checkbox': CheckboxProperty,
    'url': UrlProperty,
    'email': EmailProperty,
    'phone_number': PhoneNumberProperty,
    'formula': FormulaProperty,
    'relation': RelationProperty,
    'rollup': RollupProperty,
    'created_time': CreatedTimeProperty,
    'created_by': CreatedByProperty,
    'last_edited_time': LastEditedTimeProperty,
    'last_edited_by': LastEditedBy,
}

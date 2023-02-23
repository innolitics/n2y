import logging

from n2y.blocks import ToggleBlock
from n2y.errors import UseNextClass


plugin_data_key = "n2y.plugins.hiddenjinjatoggles"

logger = logging.getLogger(__name__)


class ExpandBlueToggleBlock(ToggleBlock):
    def __init__(self, client, notion_data, page, get_children=True):
        super().__init__(client, notion_data, page, get_children)
        if self.notion_type_data["color"] != "blue_background":
            raise UseNextClass()

    def to_pandoc(self):
        return self.children_to_pandoc()


notion_classes = {
    "blocks": {"toggle": ExpandBlueToggleBlock},
}

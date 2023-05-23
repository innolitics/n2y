"""
Work with Open Office XML format documents.
"""
import logging
from textwrap import dedent
from xml.etree import ElementTree
import zipfile

logger = logging.getLogger(__name__)

ElementTree.register_namespace(
    "cp", "http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
)
ElementTree.register_namespace("dc", "http://purl.org/dc/elements/1.1/")
ElementTree.register_namespace(
    "", "http://schemas.openxmlformats.org/package/2006/metadata/custom-properties"
)
ElementTree.register_namespace(
    "", "http://schemas.openxmlformats.org/officeDocument/2006/custom-properties"
)
ElementTree.register_namespace(
    "vt", "http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes"
)


class OpenOfficeMetadata(zipfile.ZipFile):
    def get_title(self):
        info = self.getinfo("docProps/core.xml")
        root = ElementTree.fromstring(self.read(info))
        (title_element,) = root.findall(".//{*}title")
        return " ".join(title_element.itertext())

    def set_title(self, text: str):
        info = self.getinfo("docProps/core.xml")
        root = ElementTree.fromstring(self.read(info))
        (title_element,) = root.findall(".//{*}title")
        title_element.text = text
        self.writestr(info, ElementTree.tostring(root))

    def get_template(self):
        info = self.getinfo("docProps/app.xml")
        root = ElementTree.fromstring(self.read(info))
        (template_element,) = root.findall(".//{*}Template")
        return " ".join(template_element.itertext())

    def set_template(self, text: str):
        info = self.getinfo("docProps/app.xml")
        root = ElementTree.fromstring(self.read(info))
        (template_element,) = root.findall(".//{*}Template")
        template_element.text = text
        self.writestr(info, ElementTree.tostring(root))

    def _get_custom_properties(self):
        try:
            info = self.getinfo("docProps/custom.xml")
        except KeyError:
            return {}
        root = ElementTree.fromstring(self.read(info))
        elements = root.findall(".//{*}property[@name]")
        return {e.attrib["name"]: " ".join(e.itertext()) for e in elements}

    def _set_custom_properties(self, mapping: dict[str, str]):
        mapping = dict(mapping)
        try:
            info = self.getinfo("docProps/custom.xml")
        except KeyError:
            info = None
        if info:
            root = ElementTree.fromstring(self.read(info))
            for element in root.findall(".//{*}property[@name]"):
                if (name := element.attrib["name"]) in mapping:
                    # TODO: I suppose strictly, this would deserve its own namespace
                    match (value := mapping.pop(name)):
                        case str():
                            element.text = value
                            element.attrib["type"] = "str"
                        case tuple() | list():
                            element.text = ",".join(value)
                            element.attrib["type"] = "str"
                        case _:
                            logger.error("Ignoring %r=%r", name, value)
        else:
            info = "docProps/custom.xml"
            root = ElementTree.fromstring(
                dedent(
                    """\
                    <?xml version="1.0" encoding="UTF-8"?>
                    <Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/custom-properties"
                                xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">
                    </Properties>
                    """
                )
            )
        parent = root
        for name, value in mapping.items():
            # TODO: I suppose strictly, this would deserve its own namespace
            match value:
                case str():
                    element = ElementTree.Element(
                        "{http://schemas.openxmlformats.org/officeDocument/2006/custom-properties}property",
                        attrib={"name": name, "type": "str"},
                    )
                    element.text = value
                    parent.append(element)
                case _:
                    logger.error("Ignoring %r=%r", name, value)
        self.writestr(info, ElementTree.tostring(root))

    def __getitem__(self, key):
        match key:
            case "title":
                return self.get_title()
            case "template":
                return self.get_template()
            case _:
                return self._get_custom_properties()[key]

    def __setitem__(self, key, value):
        self.update({key: value})

    def update(self, mapping):
        if "title" in mapping:
            self.set_title(mapping.pop("title"))
        if "template" in mapping:
            self.set_template(mapping.pop("template"))
        if mapping:
            self._set_custom_properties(mapping)


if __name__ == "__main__":
    from pprint import pprint
    import sys

    _, *args = sys.argv
    for path in args:
        print(path)
        oof = OpenOfficeMetadata(path)
        pprint(
            {
                "title": oof["title"],
                "template": oof["template"],
                **oof._get_custom_properties(),
            }
        )
        print()

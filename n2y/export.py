"""
This module contains all the code responsible for exporting `page.Page` and
`database.Database` objects into the various supported file formats.
"""
import os
import logging

from pandoc.types import Table
import yaml

from n2y.utils import (
    pandoc_format_to_file_extension,
    pandoc_write_or_log_errors,
    sanitize_filename,
)

logger = logging.getLogger(__name__)


def _page_properties(
    page,
    pandoc_format=None,
    id_property=None,
    url_property=None,
    property_map=None,
):
    if pandoc_format is None:
        pandoc_format = "markdown"
    if property_map is None:
        property_map = {}
    properties = page.properties_to_values(pandoc_format)
    if id_property in properties:
        logger.warning(
            'The id property "%s" is shadowing an existing '
            "property with the same name",
            id_property,
        )
    if id_property:
        properties[id_property] = page.notion_id

    if url_property in properties:
        logger.warning(
            'The url property "%s" is shadowing an existing '
            "property with the same name",
            url_property,
        )
    if url_property:
        properties[url_property] = page.notion_url
    for original, new in property_map.items():
        if original in properties:
            properties[new] = properties.pop(original)
        else:
            msg = "Property %s not found in page %s; skipping remapping from %s to %s"
            logger.warning(msg, original, page.notion_url, original, new)
    return properties


def export_page(
    page,
    pandoc_format,
    pandoc_options,
    yaml_front_matter=True,
    id_property=None,
    url_property=None,
    property_map=None,
):
    pandoc_ast = page.to_pandoc()

    if (number_empty_headers := _count_headerless_tables(pandoc_ast)) > 0:
        if "markdown" in pandoc_format or "gfm" in pandoc_format:
            logger.warning(
                "%d table(s) will present empty headers to maintain Markdown spec (%r)",
                number_empty_headers,
                page.notion_url,
            )

    page_content = pandoc_write_or_log_errors(pandoc_ast, pandoc_format, pandoc_options)
    if isinstance(page_content, str) and yaml_front_matter:
        page_properties = _page_properties(
            page,
            pandoc_format,
            id_property,
            url_property,
            property_map,
        )
        return "\n".join(
            [
                "---",
                yaml.dump(page_properties) + "---",
                page_content,
            ]
        )
    else:
        # if the result is a binary file, return it as is (since we can't add YAML metadata to it)
        return page_content


def _count_headerless_tables(pandoc_ast):
    """
    Count the number of tables in the AST that will result in empty
    header rows prepended by Pandoc.
    """
    number_empty_headers = 0
    if pandoc_ast and any(isinstance(e, Table) for e in pandoc_ast[1]):
        for element in pandoc_ast[1]:
            if isinstance(element, Table):
                _, head = element[3]
                # We do count empty rows
                number_header_rows = sum(1 for _, row in head)
                if number_header_rows == 0:
                    number_empty_headers += 1
    return number_empty_headers


def database_to_yaml(
    database,
    pandoc_format,
    pandoc_options,
    notion_filter=None,
    notion_sorts=None,
    id_property=None,
    url_property=None,
    content_property=None,
    property_map=None,
):
    if content_property in database.schema:
        logger.warning(
            'The content property "%s" is shadowing an existing '
            "property with the same name",
            content_property,
        )
    results = []
    for page in database.children_filtered(notion_filter, notion_sorts):
        result = _page_properties(
            page, pandoc_format, id_property, url_property, property_map
        )
        if content_property:
            pandoc_ast = page.to_pandoc()
            if pandoc_ast:
                result[content_property] = pandoc_write_or_log_errors(
                    pandoc_ast,
                    pandoc_format,
                    pandoc_options,
                )
            else:
                result[content_property] = None
        results.append(result)
    return results


def database_to_files(
    database,
    directory,
    pandoc_format,
    pandoc_options,
    yaml_front_matter=True,
    filename_template=None,
    notion_filter=None,
    notion_sorts=None,
    id_property=None,
    url_property=None,
    property_map=None,
):
    seen_file_names = set()
    counts = {"unnamed": 0, "duplicate": 0}
    for page in database.children_filtered(notion_filter, notion_sorts):
        page_filename = _page_filename(page, pandoc_format, filename_template)
        if page_filename:
            if page_filename not in seen_file_names:
                seen_file_names.add(page_filename)
                document = export_page(
                    page,
                    pandoc_format,
                    pandoc_options,
                    yaml_front_matter,
                    id_property,
                    url_property,
                    property_map,
                )
                write_document(document, os.path.join(directory, page_filename))
            else:
                logger.warning(
                    'Skipping page named "%s" since it has been used', page_filename
                )
                counts["duplicate"] += 1
        else:
            counts["unnamed"] += 1
    for key, count in counts.items():
        if count > 0:
            logger.info("%d %s page(s) skipped", count, key)


def write_document(document, path):
    if isinstance(document, bytes):
        file_mode = "wb"
    else:
        file_mode = "w"
    if os.path.dirname(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, file_mode) as f:
        f.write(document)


def _page_filename(page, pandoc_format, filename_template=None):
    page_title = page.title.to_plain_text()
    if filename_template is None:
        extension = pandoc_format_to_file_extension(pandoc_format)
        return sanitize_filename(f"{page_title}.{extension}")
    else:
        page_properties = page.properties_to_values()
        if "TITLE" not in page_properties:
            page_properties["TITLE"] = page_title
        try:
            return sanitize_filename(filename_template.format(**page_properties))
        except KeyError:
            logger.warning(
                'Invalid filename property, "%s". Valid options are %s',
                filename_template,
                ", ".join(page.properties.keys()),
            )
            return _page_filename(page, pandoc_format)

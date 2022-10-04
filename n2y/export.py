"""
This module contains all the code responsible for exporting `page.Page` and
`database.Database` objects into the various supported file formats.
"""
import os
import logging

import yaml

from n2y.utils import pandoc_write_or_log_errors, sanitize_filename

logger = logging.getLogger(__name__)


def _page_properties(page, id_property=None, url_property=None, property_map=None):
    if property_map is None:
        property_map = {}
    properties = page.properties_to_values()
    if id_property in properties:
        logger.warning(
            'The id property "%s" is shadowing an existing '
            'property with the same name', id_property,
        )
    if id_property:
        properties[id_property] = page.notion_id

    if url_property in properties:
        logger.warning(
            'The url property "%s" is shadowing an existing '
            'property with the same name', url_property,
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
    id_property=None,
    url_property=None,
    property_map=None,
):
    page_properties = _page_properties(page, id_property, url_property, property_map)
    pandoc_ast = page.to_pandoc()
    page_content = pandoc_write_or_log_errors(pandoc_ast, pandoc_format, pandoc_options)
    return '\n'.join([
        '---',
        yaml.dump(page_properties) + '---',
        page_content,
    ])


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
            'property with the same name', content_property,
        )
    results = []
    for page in database.children_filtered(notion_filter, notion_sorts):
        result = _page_properties(page, id_property, url_property, property_map)
        if content_property:
            pandoc_ast = page.to_pandoc()
            if pandoc_ast:
                result[content_property] = pandoc_write_or_log_errors(
                    pandoc_ast, pandoc_format, pandoc_options,
                )
            else:
                result[content_property] = None
        results.append(result)
    return yaml.dump(results, sort_keys=False)


def database_to_markdown_files(
    database,
    directory,
    pandoc_format,
    pandoc_options,
    filename_property=None,
    notion_filter=None,
    notion_sorts=None,
    id_property=None,
    url_property=None,
    property_map=None,
):
    os.makedirs(directory, exist_ok=True)
    seen_file_names = set()
    counts = {'unnamed': 0, 'duplicate': 0}
    for page in database.children_filtered(notion_filter, notion_sorts):
        page_filename = _page_filename(page, filename_property)
        if page_filename:
            if page_filename not in seen_file_names:
                seen_file_names.add(page_filename)
                with open(os.path.join(directory, f"{page_filename}.md"), 'w') as f:
                    document = export_page(
                        page,
                        pandoc_format,
                        pandoc_options,
                        id_property,
                        url_property,
                        property_map,
                    )
                    f.write(document)
            else:
                logger.warning('Skipping page named "%s" since it has been used', page_filename)
                counts['duplicate'] += 1
        else:
            counts['unnamed'] += 1
    for key, count in counts.items():
        if count > 0:
            logger.info("%d %s page(s) skipped", count, key)


def _page_filename(page, filename_property):
    # TODO: switch to using the database's natural keys as the file names
    if filename_property is None:
        return sanitize_filename(page.title.to_plain_text())
    elif filename_property in page.properties:
        return sanitize_filename(page.properties[filename_property].to_value())
    else:
        logger.warning(
            'Invalid filename property, "%s". Valid options are %s',
            filename_property, ", ".join(page.properties.keys()),
        )
        return sanitize_filename(page.title.to_plain_text())

import functools
import re
from time import sleep
import yaml
import logging
from datetime import datetime
import numbers

import pandoc
from pandoc.types import Str, Space, MetaString, MetaBool, MetaList, MetaMap, Meta
from plumbum import ProcessExecutionError

from n2y.errors import HTTPResponseError, PandocASTParseError


logger = logging.getLogger(__name__)
# see https://pandoc.org/MANUAL.html#exit-codes
PANDOC_PARSE_ERROR = 64


def process_notion_date(notion_date):
    if notion_date is None:
        return None
    elif notion_date.get('end', None):
        return [
            notion_date['start'],
            notion_date['end'],
        ]
    else:
        return notion_date['start']


def processed_date_to_plain_text(processed_date):
    # TODO: make this work the same way that Notion does
    if processed_date is None:
        return ""
    if isinstance(processed_date, list):
        return f'{processed_date[0]} to {processed_date[1]}'
    else:
        return processed_date


def pandoc_ast_to_markdown(pandoc_ast):
    # This function tries to avoid calling the separate pandoc binary (which is
    # slow) for basic cases with just spaces and strings
    if pandoc_ast is None or pandoc_ast == []:
        return ""
    elif type(pandoc_ast) == list and all(type(n) in [Str, Space] for n in pandoc_ast):
        # TODO: optimize performance for some other basic cases
        return ''.join(
            ' ' if isinstance(n, Space) else n[0]
            for n in pandoc_ast
        )
    else:
        return pandoc_write_or_log_errors(
            pandoc_ast,
            format='markdown',
            options=[
                '--wrap', 'none',  # don't hard line-wrap
                '--columns', '10000',  # The default column width is 72 characters.
                # When the width is this small, then pandoc may elect to generate HTML
                # tables in markdown instead of text-based tables; this is problematic
                # when we then convert the markdown into DOCX files which don't support raw HTML.
                '--eol', 'lf',  # use linux-style line endings
            ],
        )


def pandoc_ast_to_html(pandoc_ast):
    return pandoc_write_or_log_errors(
        pandoc_ast,
        format='html+smart',
        options=[],
    )


def pandoc_write_or_log_errors(pandoc_ast, format, options):
    if pandoc_ast is None or pandoc_ast == []:
        return ""
    try:
        # TODO: add a mechanism to customize this
        return pandoc.write(pandoc_ast, format=format, options=options)
    except ProcessExecutionError as err:
        if err.retcode == PANDOC_PARSE_ERROR:
            lines = []
            # TODO: update this code to make it not print so much
            for element, path in pandoc.iter(pandoc_ast, path=True):
                path_str = ".".join(str(i) for _, i in path)
                lines.append(f"{path_str} {element}")
                logger.error("Pandoc AST:\n%s", "\n".join(lines))
            msg = (
                "Pandoc couldn't parse the generated AST. "
                f"This is likely due to a bug in n2y or a plugin: {err.stderr}"
            )
            logger.error(msg)
            raise PandocASTParseError(msg)
        else:
            raise


def yaml_to_meta_value(data):
    """
    Convert a Python object to a Pandoc metadata values, following the approach used by
    `yamlToMetaValue` here:

    https://github.com/jgm/pandoc/blob/main/src/Text/Pandoc/Readers/Metadata.hs.

    Note that all scalars end up as strings.
    """
    if isinstance(data, str):
        return MetaString(data)
    elif isinstance(data, bool):
        return MetaBool(data)
    elif data is None:
        return MetaString("")
    elif isinstance(data, numbers.Number):
        return MetaString(str(data))
    elif isinstance(data, list):
        return MetaList([yaml_to_meta_value(item) for item in data])
    elif isinstance(data, dict):
        return MetaMap({key: yaml_to_meta_value(value) for key, value in data.items()})
    else:
        logger.warning("Unsupported type %s for metadata value %s", type(data), data)
        return None


def yaml_map_to_meta(data):
    assert isinstance(data, dict)
    assert all(isinstance(k, str) for k in data.keys())
    return Meta({k: yaml_to_meta_value(v) for k, v in data.items()})


def pandoc_format_to_file_extension(format):
    # split on '-' or '+' to handle formats like 'markdown+raw_tex'
    base_type = re.split(r'[-+]', format)[0]
    if base_type in [
        'markdown', 'gfm', 'commonmark', 'commonmark_x', 'markdown_github',
        'markdown_mmd', 'markdown_phpextra', 'markdown_strict'
    ]:
        return 'md'
    elif base_type in ['html', 'html5', 'html4']:
        return 'html'
    elif base_type in ['latex']:
        return 'tex'
    else:
        return base_type


def fromisoformat(datestring):
    """
    Parse Notion's datestrings, which aren't handled out of the box by
    `datetime.fromisoformat` because of the `Z` at the end of them.

    This function removes the need for a third-party library.
    """
    if datestring.endswith('Z'):
        return datetime.fromisoformat(datestring[:-1] + '+00:00')
    else:
        return datetime.fromisoformat(datestring)


def sanitize_filename(filename):
    """Taken from django."""
    s = str(filename).strip().replace(" ", "_")
    s = re.sub(r"(?u)[^-\w.]", "", s)
    if s in {".", ".."}:
        raise ValueError("Could not derive file name from '%s'" % filename)
    return s


def header_id_from_text(header_text, existing_ids=None):
    """
    Given the plain text for a header, produce a header.

    See https://pandoc.org/MANUAL.html#extension-auto_identifiers
    """
    have_struck_letter = False

    def do_special(potential_special):
        if potential_special == "_" or potential_special == "-" or potential_special == ".":
            return potential_special
        return ""

    def do_spacing(potential_spacing):
        if potential_spacing == " " or potential_spacing == "\n":
            return "-"
        return do_special(potential_spacing)

    def do_decimal(potential_decimal):
        if potential_decimal.isdecimal():
            return potential_decimal
        return do_spacing(potential_decimal)

    def do_letter(potential_letter):
        nonlocal have_struck_letter
        if potential_letter.isalpha():
            have_struck_letter = True
            return potential_letter.lower()
        if not have_struck_letter:
            return ""
        return do_decimal(potential_letter)

    new_header_text = ""
    for symbol in header_text:
        new_header_text += do_letter(symbol)

    if len(new_header_text) == 0:
        new_header_text = "section"

    if existing_ids is not None:
        counter = 0
        duplicate_header_text = new_header_text
        while duplicate_header_text in existing_ids:
            counter += 1
            duplicate_header_text = f"{new_header_text}-{counter}"
        new_header_text = duplicate_header_text

    return new_header_text


def id_from_share_link(share_link):
    hyphens_removed = strip_hyphens(share_link)
    if not hyphens_removed.startswith("https://www.notion.so/"):
        return hyphens_removed
    else:
        domain_removed = hyphens_removed.split("/")[-1]
        query_removed = domain_removed.split("?")[0]
        assert len(query_removed) >= 32
        return query_removed[-32:]


def share_link_from_id(id):
    # Note that ordinarily page links include a hyphenated titled, but
    # fortunately they will redirect to the canonical page URL including the
    # hyphenated title if you visit the link with only the UUID. Similarly,
    # database urls often have a version parameter, but we can omit that too.
    return f"https://www.notion.so/{id}"


def strip_hyphens(string):
    return string.replace("-", "")


def load_yaml(data):
    try:
        return yaml.load(data, Loader=yaml.SafeLoader)
    except yaml.YAMLError as e:
        raise ValueError('"{}" contains invalid YAML: {}'.format(data, e))


def retry_api_call(api_call):
    max_api_retries = 4

    @functools.wraps(api_call)
    def wrapper(*args, retry_count=0, **kwargs):
        assert "retry_count" not in kwargs, "retry_count is a reserved keyword"
        try:
            return api_call(*args, **kwargs)
        except HTTPResponseError as err:
            should_retry = err.status in [409, 429, 500, 502, 504]
            if not should_retry:
                raise err
            elif retry_count < max_api_retries:
                retry_count += 1
                if 'retry-after' in err.headers:
                    retry_after = float(err.headers['retry-after'])
                    logger.info(
                        'This API call has been rate limited and '
                        'will be retried in %f seconds. Attempt %d of %d.',
                        retry_after, retry_count, max_api_retries,
                    )
                else:
                    retry_after = 2
                    logger.info(
                        'This API call failed and '
                        'will be retried in %f seconds. Attempt %d of %d.',
                        retry_after, retry_count, max_api_retries,
                    )
                sleep(retry_after)
                return wrapper(*args, retry_count=retry_count, **kwargs)
            else:
                raise err
    return wrapper

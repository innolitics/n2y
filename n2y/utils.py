from datetime import datetime
import logging
import re

import pandoc
from pandoc.types import Str, Space
from plumbum import ProcessExecutionError

from n2y.errors import PandocASTParseError


logger = logging.getLogger(__name__)


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


# see https://pandoc.org/MANUAL.html#exit-codes
PANDOC_PARSE_ERROR = 64


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
        try:
            # TODO: add a mechanism to customize this
            result = pandoc.write(
                pandoc_ast,
                format='gfm+tex_math_dollars+raw_attribute',
                options=[
                    '--wrap', 'none',  # don't hard line-wrap
                    '--eol', 'lf',  # use linux-style line endings
                ],
            )
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
        return result


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


def strip_dashes(string):
    return string.replace("-", "")

from datetime import datetime
import logging

import pandoc
from pandoc.types import Str, Space


logger = logging.getLogger(__name__)


def pandoc_ast_to_markdown(pandoc_ast):
    # This function tries to avoid calling the separate pandoc binary (which is
    # slow) for basic cases with just spaces and strings
    if len(pandoc_ast) == 0:
        return ""
    elif all(type(n) in [Str, Space] for n in pandoc_ast):
        # TODO: optimize performance for some other basic cases
        return ''.join(
            ' ' if isinstance(n, Space) else n[0]
            for n in pandoc_ast
        )
    else:
        result = pandoc.write(
            pandoc_ast,
            format='gfm+tex_math_dollars',
            options=['--wrap', 'none'],  # don't hard line-wrap
        ).replace('\r\n', '\n')
        logger.debug("%s", result)
        logger.debug("%s", repr(pandoc_ast))
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

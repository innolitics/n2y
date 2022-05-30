from datetime import datetime

import pandoc


def pandoc_ast_to_markdown(pandoc_ast):
    return pandoc.write(
        pandoc_ast,
        format='gfm+tex_math_dollars',
        options=['--wrap', 'none'],  # don't hard line-wrap
    ).replace('\r\n', '\n')


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

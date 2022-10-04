import sys
from io import StringIO

from tests.utils import NOTION_ACCESS_TOKEN
from n2y.audit import main


def run_n2yaudit(arguments):
    old_stdout = sys.stdout
    sys.stdout = StringIO()
    try:
        status = main(arguments, NOTION_ACCESS_TOKEN)
        stdout = sys.stdout.getvalue()
    finally:
        sys.stdout = old_stdout
    return status, stdout


def test_audit():
    '''
    The database can be seen here:
    https://fresh-pencil-9f3.notion.site/Audited-cfa8ff07bba244c8b967c9b6a7a954c1
    '''
    object_id = 'cfa8ff07bba244c8b967c9b6a7a954c1'
    status, stdoutput = run_n2yaudit([object_id])
    assert status == 3

    external_mention_in_top_page = \
        'https://www.notion.so/Audited-cfa8ff07bba244c8b967c9b6a7a954c1#aa4fa886f8244c818de8018bb3491806'  # noqa: E501
    external_mention_in_child_page = \
        'https://www.notion.so/Child-f3e3628fc80c470ea68994fa7ec0ff17#d1d32ff6f0cb4c71a2f1c4ec55e00086'  # noqa: E501
    internal_mention_in_child_page = \
        'https://www.notion.so/Child-f3e3628fc80c470ea68994fa7ec0ff17#eab91ccc32924221ac3f0a74225a33dd'  # noqa: E501
    external_mention_in_child_database = \
        'https://www.notion.so/B-4412005dcec24ff2827abbc367c90b29#6373a0b5c2804fbe9dfac167ce6948a0'  # noqa: E501
    internal_mention_in_database_in_column = \
        'https://www.notion.so/Audited-cfa8ff07bba244c8b967c9b6a7a954c1#21a13c06ef86462e882a181c6cb52a64'  # noqa: E501

    # NOTE: When you try to get a link for a "LinkToPageBlock" in the Notion UI,
    # it appears to give you the URL for the linked page or database, and not to
    # the block itself. Thus, these two links were extracted using a debugger
    # when running this test.

    external_link_in_top_page = \
        'https://www.notion.so/Audited-cfa8ff07bba244c8b967c9b6a7a954c1#c22d76d50c704761b0e729531e6cc24b'  # noqa: E501
    internal_link_in_top_page = \
        'https://www.notion.so/Audited-cfa8ff07bba244c8b967c9b6a7a954c1#3e2e2fb2e9bf4a1f8b00bbb18a9d97e9'  # noqa: E501

    assert external_mention_in_top_page in stdoutput
    assert external_mention_in_child_page in stdoutput
    assert internal_mention_in_child_page not in stdoutput
    assert external_mention_in_child_database in stdoutput
    assert internal_mention_in_database_in_column not in stdoutput
    assert external_link_in_top_page in stdoutput
    assert internal_link_in_top_page not in stdoutput

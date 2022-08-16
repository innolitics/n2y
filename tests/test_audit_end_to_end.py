import sys
from io import StringIO

from tests.utils import NOTION_ACCESS_TOKEN
from n2y.audit import main


def run_n2y(arguments):
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    sys.stdout = StringIO()
    sys.stderr = StringIO()
    try:
        status = main(arguments, NOTION_ACCESS_TOKEN)
        stdout = sys.stdout.getvalue()
        stderr = sys.stderr.getvalue()
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr
    return status, stdout, stderr


external_link_in_top_page = \
    'https://notion.so/Audited-cfa8ff07bba244c8b967c9b6a7a954c1#aa4fa886f8244c818de8018bb3491806'
external_link_in_child_page = \
    'https://notion.so/Child-f3e3628fc80c470ea68994fa7ec0ff17#d1d32ff6f0cb4c71a2f1c4ec55e00086'
internal_link_in_child_page = \
    'https://notion.so/Child-f3e3628fc80c470ea68994fa7ec0ff17#eab91ccc32924221ac3f0a74225a33dd'
external_link_in_child_database = \
    'https://notion.so/B-4412005dcec24ff2827abbc367c90b29#6373a0b5c2804fbe9dfac167ce6948a0'


def test_audit():
    '''
    The database can be seen here:
    https://fresh-pencil-9f3.notion.site/Audited-cfa8ff07bba244c8b967c9b6a7a954c1
    '''
    object_id = 'cfa8ff07bba244c8b967c9b6a7a954c1'
    status, stdoutput, _ = run_n2y([object_id])
    assert status == 3

    assert external_link_in_top_page in stdoutput
    assert external_link_in_child_page in stdoutput
    assert internal_link_in_child_page not in stdoutput
    assert external_link_in_child_database in stdoutput

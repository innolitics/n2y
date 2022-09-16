import logging
import os
import sys
import sqlite3
import pickle

from os.path import exists

from n2y import notion
from n2y.notion_mocks import mock_id, mock_page

from unittest import mock

from n2y.plugins import expandlinktopages

from n2y.main import main

"""
For testing only
Launch n2y programmatically, with specified arguments.
"""

logging.basicConfig()

global logger

logger = logging.getLogger(__name__)


#  Constants to be put in .env file or the equivalent.  But then again, this is just a test.
access_token = "secret_gke3p6v6mCWl7UmEjnTAoTCet3BxLQaWZeSWicWA1a8"
linked_page_id = "8a0d7356c4ff45f48b985d145775f3a0"
# linked_page_id = "56850767f7b645baaffddfc1ff617db1"
plugin_id = "n2y.plugins.linktopage"
# https://www.notion.so/mountjoy/Test-subpage-8a0d7356c4ff45f48b985d145775f3a0

# Just curious to have a look at these data elements.
raw_args = [linked_page_id, "--plugin", plugin_id]
# Nice!  a tidy string of argument values, including our own linked_page_id.

# Another way to initialize arguments to our liking.
args = raw_args

# Bare bones client.
cl = notion.Client(access_token)

cache_file = ".n2ycache"
table_name = "assets"
dump_file = ".test"

file_exists = exists(cache_file)

# Create or connect to cache file.
connection = sqlite3.connect(cache_file)


# Prepare to send SQL statements
cursor = connection.cursor()

# This test for table existence does not work: 
# cursor.execute(f"SELECT name FROM {cache_file} WHERE type='table' AND name='{table_name}'")

cursor.execute("CREATE TABLE if not exists fish (name TEXT, species TEXT, tank_number INTEGER)")
cursor.execute("INSERT INTO fish VALUES ('Sammy', 'shark', 1)")
cursor.execute("INSERT INTO fish VALUES ('Jamie', 'cuttlefish', 7)")

# Now we are able to instatiantate our page object.
page = cl.get_page(linked_page_id)

# Basic file handling. "wb" = write bytes
file = open(dump_file, "wb")
pickle.dump(page, file)
file.close()

page2 = mock_page()


# Here we have a notion type of child_page and the notion page id that we fed it.
block = cl.get_block(linked_page_id, page)

# This one gets it from Client, the top class.
# using the Client.get_block method, as above
# Now just to insert it into the page.

# This is just a work around for me

# linktopage(cl, notion_data, page)


access_token = os.environ.get('NOTION_ACCESS_TOKEN', None)
sys.exit(main(args, access_token))
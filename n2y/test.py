import logging
import os
import sys
import sqlite3
import pickle

import json

from datetime import datetime

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

try:
    # Create or connect to cache file.
    connection = sqlite3.connect(cache_file)
except: 
    None

# Prepare to send SQL statements
cursor = connection.cursor()

time = datetime.now()

timestamp = datetime.timestamp(time)


# There is no ENUM data type in sqlite
create_table_query = (
    "CREATE TABLE IF NOT EXISTS assets (" 
    "id int, "
    "entity_id varchar(64), "
    "entity_last_modified DATETIME, "
    "entity_data BLOB, "
    "entity_type varchar(16) )"
    )
 

add_row_query = (
    "INSERT INTO assets (entity_id, entity_time) "
    "VALUES ("
    f"{mock_id()} as entity_id, "
    f"{timestamp} as entity_time, "
    ")"
)


def convert_to_binary(filename):
    with open(filename, 'rb') as file:
        binary_data = file.read()
    return binary_data


def insertBLOB(empId, name, photo, resumeFile):
    try:
        sqliteConnection = sqlite3.connect('SQLite_Python.db')
        cursor = sqliteConnection.cursor()
        print("Connected to SQLite")
        sqlite_insert_blob_query = """ INSERT INTO new_employee
                                  (id, name, photo, resume) VALUES (?, ?, ?, ?)"""

        empPhoto = convert_to_binary(photo)
        resume = convert_to_binary(resumeFile)
        # Convert data into tuple format
        data_tuple = (empId, name, empPhoto, resume)
        cursor.execute(sqlite_insert_blob_query, data_tuple)
        sqliteConnection.commit()
        print("Image and file inserted successfully as a BLOB into a table")
        cursor.close()

    except sqlite3.Error as error:
        print("Failed to insert blob data into sqlite table", error)
    finally:
        if sqliteConnection:
            sqliteConnection.close()
            print("the sqlite connection is closed")

#insertBLOB(1, "Smith", "E:\pynative\Python\photos\smith.jpg", "E:\pynative\Python\photos\smith_resume.txt")
#insertBLOB(2, "David", "E:\pynative\Python\photos\david.jpg", "E:\pynative\Python\photos\david_resume.txt") 

cursor.execute(create_table_query)

cursor.execute(add_row_query)

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
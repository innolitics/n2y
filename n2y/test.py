import logging

from n2y import notion

from n2y.plugins import linktopage

"""
For testing only
Launch n2y programmatically, with specified arguments.
"""

logging.basicConfig()

global logger

logger = logging.getLogger(__name__)

logger.critical("At least I'm logging!")


#  Constants to be put in .env file or the equivalent.  But then again, this is just a test.
access_token = "secret_gke3p6v6mCWl7UmEjnTAoTCet3BxLQaWZeSWicWA1a8"
linked_page_id = "56850767f7b645baaffddfc1ff617db1"
plugin_id = "n2y.plugins.linktopage"


# Just curious to have a look at these data elements.
raw_args = [linked_page_id, "--plugin", plugin_id]
# Nice!  a tidy string of argument values, including our own linked_page_id.

# Another way to initialize arguments to our liking.
args = raw_args

# Bare bones client.
cl = notion.Client(access_token)

# Now we are able to instatiantate our page object.
cl.get_page(linked_page_id)

# Some experiments
page = cl.get_page(linked_page_id)

# Here we have a notion type of child_page and the notion page id that we fed it.
cl.get_block(linked_page_id, page)

# This one gets it from Client, the top class.
# using the Client.get_block method, as above
# Now just to insert it into the page.

# This is just a work around for me

x = linktopage

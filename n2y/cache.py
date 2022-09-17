import logging
import sqlite3

from datetime import datetime

logger = logging.getLogger(__name__)

class Cache:

    def __init__(self, client):
        
        self.client = client
        self.cache_file = ".n2ycache"
        self.table_name = "assets"


    def add_to_cache(self, entity_id):
    
        try:
            # Create or connect to cache file.
            connection = sqlite3.connect(self.cache_file)
        except: 
            logger.warning("Error opening connection")
            return None

        # [If table "cache" does not exist, create it]
        # _create_cache_table()

        add_row_query = (
            "INSERT INTO assets (entity_id, entity_time) "
            "VALUES ("
            f"{entity_id}, "
            f"{timestamp},"
            ")"
        )

        # Get current time stamp to save to cache.
        # Maybe want to use last modified time from Notion block.
        timestamp = datetime.timestamp(datetime.now())

        # Prepare to send SQL statements
        cursor = connection.cursor()

        cursor.execute(add_row_query)

        connection.close()


    def get_from_cache(entity_id):
        None

    def _create_cache_table(self):
        

        try:
            # Create or connect to cache file.
            connection = sqlite3.connect(self.cache_file)
        except: 
            logger.warning("Error opening connection")
            return None

        # There is no ENUM data type in sqlite
        create_table_query = (
            "CREATE TABLE IF NOT EXISTS assets (" 
            "id int, "
            "entity_id varchar(64), "
            "entity_last_modified DATETIME, "
            "entity_data BLOB, "
            "entity_type varchar(16) )"
        )
 
        cursor = connection.cursor()
        cursor.execute(create_table_query)

        connection.close()
        
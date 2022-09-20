import logging
import sqlite3
import pickle
import datetime
import time

from os.path import exists

from datetime import datetime

logger = logging.getLogger(__name__)

class Cache:
    """Cache Notion block entities in local storage"""

    def __init__(self, client):
        
        self.client = client
        self.cache_file = ".n2ycache"
        self.table_name = "assets"
        self.no_cache = client.no_cache
        self.schema = ("CREATE TABLE assets ("
            "id INTEGER , "
            "entity_id VARCHAR(64) UNIQUE, "
            "last_edited_time DATETIME, "
            "data BLOB, "
            "entity_type VARCHAR(16), "
            "timestamp DEFAULT CURRENT_TIMESTAMP, "
            "cache_last_updated DATETIME, "
            "PRIMARY KEY('id' AUTOINCREMENT) )"
        )

        # This will hold the timestamp of the item most recently retrieved or
        # saved to the cache. 
        self.timestamp = None
        # Here's what the schema looks like in sqlite.  Looks like
        # a literal copy of what we passed in. 
        # CREATE TABLE assets (id INTEGER , entity_id VARCHAR(64) UNIQUE, last_edited_time DATETIME, data BLOB, entity_type VARCHAR(16), timestamp DEFAULT CURRENT_TIMESTAMP, cache_last_updated DATETIME, PRIMARY KEY('id' AUTOINCREMENT) )
        self.cursor = None 

        # TODO: look at this function, in particular, how it exists.
        self._connect_cache()


        # TODO: Just thinking I'm sure there are many efficiency things I missed.



    def add_to_cache(self, entity_id, notion_block, last_edited_time, entity_type="block"):


        # TODO: If we're going to update the timestamp attribute each time 
        # an entity is saved to the cache, we'll need to retrieve it after it is 
        # created, or send it in with the insert statement. 

        add_row_query = ("INSERT INTO assets "
            "(entity_id, last_edited_time, data, entity_type) "
            "VALUES (?, ?, ?, ?)"
        )


        # When we create the cached entry we'll also condense the block to binary.
        query_values = (entity_id, last_edited_time, pickle.dumps(notion_block), entity_type)


        try:
            self.cursor.execute(add_row_query, query_values)
            self.connection.commit()
        except self.connection.Error as error: 
                logger.warning('Cache error: Failed to save block to cache.', error)
  



#TODO should return 

    def get_from_cache(self, entity_id):

        """ Retrieve cached entity
        
        If cache is off, then get fresh data instead. """
            
        # If cache is on ...
        if not self.no_cache:
        
            # Search the cache for a matching entity.
            self.cursor.execute(
                f"SELECT data, timestamp FROM assets WHERE entity_id = '{entity_id}';"
                )
            rows = self.cursor.fetchall()

            ## If entity found in cache...
            if rows: 

                self.timestamp = rows[0][1]

                # Unpickle the block data
                return pickle.loads(rows[0][0])
    

        # If we get down here, then the cache data is unavailable
        # for some reason and we must get the block from the source.
        # We'll also save the block to the cache now.
        entity = self.client.get_notion_block(entity_id)

        # Need the timestamp to be in sql/linux format. 
        date_time = datetime.now()

        self.timestamp = time.mktime(date_time.timetuple())

        return entity

     
    def get_notion_block(self, block_id):
        # TODO: Not sure if there will be another use for
        # get_from_cache.  If not, then consolidate these two methods.

        return self.get_from_cache(block_id), self.timestamp


    def get_child_notion_blocks(self, parent_block_id):

        # returns a list

        # Now I'm thinking that child blocks will be stored in the data field of
        # their parent block, which means to get the cached value we'd have to 
        # pull the whole block and decode it....

       # get_child_blocks = "SELECT .. WHERE entity_id = '{parent_block_id}'"

      #  [self.add_to_cache(block_id, x, last_edited_time) for x in child_notion_blocks]

       #     return self.get_from_cache(block_id)
        None



    def cache_notion_block(self, block_id, notion_block, last_edited_time): 

        self.add_to_cache(block_id, notion_block, last_edited_time)

    def timestamp(self):
        return self.timestamp


    def cache_child_notion_blocks(self, block_id, child_notion_blocks, last_edited_time): 
       
       # child_notion_blocks is a list of blocks.
       # add them all to the cache.

        [self.add_to_cache(block_id, x, last_edited_time) for x in child_notion_blocks]


    def _create_cache_table(self):
      
        # The cache file did not exist.  Create table. 
        # TODO: Add indexes to any of the fields below that do not already have one yet
        # are likely to be searched.

        self.cursor.execute("DROP TABLE IF EXISTS assets")
        create_table_query = (self.schema)

        self.cursor.execute(create_table_query)


    def _validate_cache(self): 

        """ Check structure of assets table against current schema. """

        get_schema_query = "SELECT sql FROM sqlite_master WHERE name = 'assets'"

        self.cursor.execute(get_schema_query)

        rows = self.cursor.fetchall()

        if len(rows) == 0:
            return False
        elif rows != self.schema:
            return False
        else:
            return True


    def _update_cache(self, entity):

        # TODO: Fill in here
        None


    def _connect_cache(self):

        # If cache file does not exist, we'll create it.  
        # But we'd like to know here if it had to be created so that we can create the table too.
        cache_state = exists(self.cache_file) 

        # TODO: Is this a case worth guarding against?  Unlikely that anything could go wrong with the sqlite call here. 
        try:
            # Create or connect to cache file.
            self.connection = sqlite3.connect(self.cache_file)
        except: 
            # TODO: is warning the right state, or should I use critical here. 
            logger.warning("Cache error: ")
            return False

        self.cursor = self.connection.cursor()

        a = self._validate_cache()

        # If the cache file did not exist, or if the cache table 
        # file structure is wrong, must create the cache table.
        if not cache_state or not self._validate_cache(): 
            self._create_cache_table()

        return True


    def clear_cache(self, entity_id = "*"):

        # Clears entire cache table, unless entity_id is specified, 
        # in which event only matching rows are cleared. 
        clear_cache_query = f"DELETE FROM assets WHERE entity_id = '{entity_id}'"

        self.cursor.execute(clear_cache_query)

        self.connection.commit()
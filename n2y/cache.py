import logging
import sqlite3
import pickle

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
        self.cursor = None # TODO: Best way to initialize this?
        # TODO: Opening cursor at this level, rather than opening and closing with each cache access. 
        # Not sure if this is the best way.
        self._connect_cache()

        # This will hold the timestamp of the item most recently retrieved or
        # saved to the cache. 
        self.timestamp = ""



    def add_to_cache(self, entity_id, notion_block, last_edited_time, entity_type):


        # TODO: If we're going to update the timestamp attribute each time 
        # an entity is saved to the cache, we'll need to retrieve it after it is 
        # created, or send it in with the insert statement. 

        add_row_query = """
            INSERT INTO assets (entity_id, last_edited_time, data, entity_type)
            "VALUES (?, ?, ?, ?) """


        # When we create the cached entry we'll also condense the block to binary.
        query_values = (entity_id, last_edited_time, pickle.dumps(notion_block), entity_type)


        try:
            self.cursor.execute(add_row_query, query_values)
            self.connection.commit()
        except self.connection.Error as error: 
                logger.warning('Cache error: Failed to save block to cache.', error)
  





    def get_from_cache(self, entity_id):

        """ Retrieve cached entity
        
        If cache is off, then get fresh data instead. """
            
        # If cache is on ...
        if not self.no_cache:
        
            # Search the cache for a matching entity.
            self.cursor.execute(
                f"SELECT * FROM assets WHERE id = {entity_id};"
                )

            rows = self.cursor.fetchall()

            ## If entity found in cache...
            if rows: 

                # Unpickle the block data
                return pickle.loads(rows["data"])
    

        # If we get down here, then the cache data is unavailable
        # for some reason and we must get the block from the source.
        # We'll also save the block to the cache now.
        entity = self.client.get_notion_block(entity_id)


        self._update_cache(entity)

        return entity

     
    def get_notion_block(self, block_id):
        # TODO: Not sure if there will be another use for
        # get_from_cache.  If not, then consolidate these two methods.
        return self.get_from_cache(block_id)


    def get_child_notion_blocks(self, block_id):

        # Get child blocks from cache, or from
        # database.

        # TODO: It's a list of blocks. ...so, we just 
        # retrieve it from the cache as we would
        # any other row, or so I'm assuming.
        # I just need to look up the structure of this part of a block.

            return self.get_from_cache(block_id)



    def cache_notion_block(self, block_id, notion_block, last_edited_time): 

        self.add_to_cache(block_id, notion_block, last_edited_time)




    def cache_child_notion_blocks(self, block_id, child_notion_blocks, last_edited_time): 
       
       # TODO: Check structure of child_notion_blocks and make sure the below
       # has a chance of working.
       # I'm assuming, and I haven't completely though it through, that 
       # we're caching the individual child blocks.  Not tied to parent block.

    # TODO: Check data structure.   Whose last edited time here?
     #   [self.add_to_cache(c.block_id, c.notion_data, c.last_edited_time) for c in child_notion_blocks]
      
        # If child notion blocks is a list of expanded blocks, then we'll just treat it 
        # as data and put it in the cache.
        # TODO: This data row will conflict with the block's own row.
        self.add_to_cache(block_id, child_notion_blocks, last_edited_time)


    def _create_cache_table(self):
      
        # The cache file did not exist.  Create table. 
        # TODO: Add indexes to any of the fields below that do not already have one yet
        # are likely to be searched.

        create_table_query = (
        "CREATE TABLE IF NOT EXISTS assets (" 
        "id int NOT NULL AUTO_INCREMENT PRIMARY KEY, "
        "entity_id VARCHAR(64) UNIQUE, "
        "last_edited_time DATETIME, " 
        "data BLOB, "
        "entity_type VARCHAR(16), "
        "timestamp DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP "
        "cache_last_updated DATETIME )"
        )

        self.cursor.execute(create_table_query)


    def _validate_cache(self, entity_id): 
        # TODO: Currently lacking a use case, but probably has one.
        
        # Check file structure of assets table against current schema.
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

        # If the cache file did not exist, must create the cache table.
        if not cache_state: 
            self._create_cache_table()

        return True
""" A global cache for milter LDAP queries
"""
import datetime


class QueryCache(object):

    """ A global cache for milter LDAP queries
    """

    cache = {}

    """ The cache """

    @staticmethod
    def get(directory_server, query):

        """ Return a cached query

        :param directory_server: The directory server, that runs the query
        :param query: The query itself
        :return: The query or None if it wasn't cached or has timed out
        """

        if directory_server.id not in QueryCache.cache or\
           query not in QueryCache.cache[directory_server.id]:

            # That item isn't cached

            return None

        # Check, if the item has timed out

        now = datetime.datetime.now()

        then = QueryCache.cache[directory_server.id][query]["timestamp"]

        if (now-then).total_seconds() > QueryCache.cache[directory_server.id]["_timeout"]:

            return None

        # Store the item

        return QueryCache.cache[directory_server.id][query]["data"]

    @staticmethod
    def set(directory_server, query, data):

        """ Add a query to the cache

        :param directory_server: The directory server, that runs the query
        :param query: The query itself
        :param data: The data returned from the query
        """

        now = datetime.datetime.now()

        if directory_server.id not in QueryCache.cache:

            # Create a basic directory server cache item and store the timeout value

            QueryCache.cache[directory_server.id] = {
                "_timeout": directory_server.cache_timeout
            }

        # Add the item to the cache

        QueryCache.cache[directory_server.id][query] = {
            "timestamp": now,
            "data": data
        }

    @staticmethod
    def flush():

        """ Walk through the cache and remove timed out values
        """

        now = datetime.datetime.now()

        for directory_server_id in list(QueryCache.cache):

            for query in list(QueryCache.cache[directory_server_id]):

                if query == "_timeout":
                    continue

                then = QueryCache.cache[directory_server_id][query]["timestamp"]

                if (now-then).total_seconds() > QueryCache.cache[directory_server_id]["_timeout"]:

                    # The cache item has timed out. Remove it.

                    del(QueryCache.cache[directory_server_id][query])

            if len(QueryCache.cache[directory_server_id]) == 1:

                # There are no cache items left. Remove the directory server.

                del(QueryCache.cache[directory_server_id])
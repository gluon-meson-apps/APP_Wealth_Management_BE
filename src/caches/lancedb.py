from caches.base import Cache
from models.embedding_model.embedding import Embedding
from typing import List, Union, Tuple
from utils.common import init_logger
import lancedb
import pyarrow as pa


class LancedbCache(Cache):
    logger = init_logger(__name__)

    def __init__(self, embedding_model: Embedding, cache_path: str, cache_table_name: str) -> None:
        self.embedding_model = embedding_model
        self.cache_path = cache_path
        self.db = lancedb.connect(cache_path)
        try:
            self.cache = self.db.open_table(cache_table_name)
        except:  # noqa: E722
            self.logger.info("No cache table found, trying to create one")
            schema = pa.schema(
                [
                    pa.field(
                        "vector",
                        pa.list_(
                            pa.float32(),
                            list_size=self.embedding_model.embedding_size * 2,
                        ),
                    ),  # note *2, to seprate system prompt and user query
                    ("system", pa.string()),
                    ("query", pa.string()),
                    ("response", pa.string()),
                ]
            )
            self.cache = self.db.create_table(name=cache_table_name, schema=schema)

    def search_cache(
        self,
        messages: List,
        exact_match: bool = False,
        similarity_score_threshold: float = 0.02,
    ) -> Union[str, None]:
        """
        Search the cache table, if found, return cached result, else, return None
        """
        self.logger.info("Searching from cache")
        system, query = self.format_query(messages)
        vector = self.calculate_vector(system, query)
        # always only return the first result
        cache_search_results = self.cache.search(vector).metric("cosine").limit(1).to_list()

        if len(cache_search_results) > 0:
            distance = cache_search_results[0]["_distance"]
            if exact_match:
                # not possible for exact zero, set a small float number
                if abs(distance) <= 1e-05:
                    self.logger.info(f"Find exact match query, the distance is {distance}")
                    return cache_search_results[0]["response"]
                else:
                    self.logger.info(f"No exact result found in cache, the min distance is {distance}")
                    return None
            else:
                if abs(distance) <= similarity_score_threshold:
                    self.logger.info(f"Find similar result in cache, the distance is {distance}")
                    return cache_search_results[0]["response"]
                else:
                    self.logger.info(f"No similar result found in cache, the min distance is {distance}")
                    return None
        else:
            self.logger.info("No result found in cache.")
            return None

    def add_cache(self, messages: List, response: str) -> None:
        self.logger.info("Adding to cache...")
        system, query = self.format_query(messages)
        vector = self.calculate_vector(system, query)
        self.cache.add(
            [
                {
                    "vector": vector,
                    "system": system,
                    "query": query,
                    "response": response,
                }
            ],
        )

    def calculate_vector(self, system: str, query: str) -> List:
        """
        Calculate and concat embedding vectors
        """
        system_vector = self.embedding_model.encode(system)
        query_vector = self.embedding_model.encode(query)
        return system_vector + query_vector

    def format_query(self, messages: List) -> Tuple[str, str]:
        """
        Format a vector database query from messages
        Concat all system and user contents
        """
        ### Note need to process system message and user message seprately ###
        system = ""
        query = ""
        for message in messages:
            if message["role"] == "system":
                system += message["content"]
            # keep function and user content together
            else:
                query += message["content"]
        return system, query

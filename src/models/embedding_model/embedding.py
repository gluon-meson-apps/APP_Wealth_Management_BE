import requests
from src.utils.common import init_logger


class Embedding:
    logger = init_logger(__name__)

    def __init__(self, endpoint) -> None:
        self.logger.debug("Init embedding")
        self.endpoint = endpoint

    def encode(self, query, model="m3e-base", normalize_embeddings=False):
        headers = {"Content-Type": "application/json", "accept": "application/json"}

        body = {
            "model": model,
            "query": query,
            "normalize_embeddings": normalize_embeddings,
        }

        try:
            self.logger.debug("Encode query with embedding")
            response = requests.post(url=self.endpoint, json=body, headers=headers, timeout=30)
            return response.json()["embeddings"]
        except Exception as e:
            self.logger.error("Embedding Error: %s", str(e), exc_info=True)
            return "Embedding Error"

    @property
    def embedding_size(self, model="m3e-base"):
        ## known embedding size for sentence transformers
        if model == "m3e-base":
            return 768
        else:
            raise Exception("Unsupported model name!")

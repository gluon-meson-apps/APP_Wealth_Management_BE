from typing import Union


class Cache:
    def search(self, content: str, exact_match: bool = False, similarity_score_threshold: float = 0.02, limit=None) -> Union[str, None]:
        raise NotImplementedError

    def add_cache(self, content: str, response: str) -> None:
        raise NotImplementedError


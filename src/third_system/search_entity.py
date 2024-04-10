from typing import Union

from pydantic import BaseModel, Extra


# todo: move to sdk later
class SearchParamFilter(BaseModel):
    field: str
    op: str
    value: Union[str, list[str]]


class SearchParamSort(BaseModel):
    field: str
    order: str


class SearchParam(BaseModel):
    query: str
    filters: Union[list[SearchParamFilter], None] = None
    fields: Union[list[str], None] = None
    sort: Union[list[SearchParamSort], None] = None
    page: Union[int, None] = None
    size: Union[int, None] = None
    configs: Union[dict, None] = None
    tags: Union[dict[str, str], None] = {}
    k: int = 4


class SearchItemReference(BaseModel, extra=Extra.allow):
    meta__source_type: str
    meta__source_name: str
    meta__source_text: str = None
    meta__source_page: int = None
    meta__source_url: Union[str, None] = None
    meta__source_sub_name: Union[str, None] = None
    meta__source_sub_type: Union[str, None] = None


class SearchItem(BaseModel, extra=Extra.allow):
    meta__score: float
    meta__reference: Union[SearchItemReference, None] = None

    def json(self):
        return {
            "meta__score": self.meta__score,
            "meta__reference": self.meta__reference.json() if self.meta__reference else None
        }


class SearchResponse(BaseModel):
    page: int = 0
    pages: int = 0
    size: int = 0
    total: int = 0
    items: list[SearchItem] = []


class KnowledgeSearchItem(BaseModel, extra=Extra.allow):
    data_set_id: int
    source: str
    search__score: float
    type: str
    field__text: str
    field__source: str


class KnowledgeSearchResponse(BaseModel):
    items: list[KnowledgeSearchItem] = []
    total: int = 0
    page: int = 0
    size: int = 0
    pages: int = 0

    def is_empty(self):
        return self.total == 0

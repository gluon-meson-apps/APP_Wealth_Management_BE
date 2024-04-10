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
    data_set_id: Union[int, None] = None
    meta__source_text: Union[str, None] = None
    meta__source_page: Union[int, None] = None
    meta__source_url: Union[str, None] = None
    meta__source_sub_name: Union[str, None] = None
    meta__source_sub_type: Union[str, None] = None
    meta__source_score: Union[float, None] = None

    def json(self):
        return {
            "data_set_id": self.data_set_id,
            "meta__source_type": self.meta__source_type,
            "meta__source_name": self.meta__source_name,
            "meta__source_text": self.meta__source_text,
            "meta__source_score": self.meta__source_score
        }


class SearchItem(BaseModel, extra=Extra.allow):
    meta__score: float
    meta__reference: Union[SearchItemReference, None] = None


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

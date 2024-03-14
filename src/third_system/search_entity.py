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


class SearchItemReference(BaseModel, extra=Extra.allow):
    meta__source_type: str
    meta__source_name: str
    meta__source_url: Union[str, None] = None
    meta__source_sub_name: Union[str, None] = None
    meta__source_sub_type: Union[str, None] = None


class SearchItem(BaseModel, extra=Extra.allow):
    meta__score: float
    meta__reference: Union[SearchItemReference, None] = None


class SearchResponse(BaseModel):
    page: int = 0
    pages: int = 0
    size: int = 0
    total: int = 0
    items: list[SearchItem] = []

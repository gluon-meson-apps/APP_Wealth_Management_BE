import pandas as pd

from third_system.search_entity import SearchItem


class DfProcessor:
    @classmethod
    def search_items_to_df(cls, search_item: list[SearchItem]) -> pd.DataFrame:
        return pd.DataFrame([item.model_dump() for item in search_item])

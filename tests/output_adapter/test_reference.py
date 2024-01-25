from output_adapter.base import process_references
from third_system.search_entity import SearchItem, SearchItemReference


def prepare_search_item_lists():
    search_item_lists = [
        SearchItem(
            meta__score=0.0,
            meta__reference=SearchItemReference(meta__source_type="csv", meta__source_name="wcs_data.csv"),
            content="Apple Inc.",
            id=1
        ),
        SearchItem(
            meta__score=0.1,
            meta__reference=SearchItemReference(meta__source_type="csv", meta__source_name="wcs_data.csv"),
            content="Google Inc.",
            id=2
        ),
        SearchItem(
            meta__score=0.2,
            meta__reference=SearchItemReference(meta__source_type="csv", meta__source_name="wcs_data.csv"),
            content="Microsoft Inc.",
            id=3
        ),
    ]
    return search_item_lists


def test_process_references():
    with open('./test_reference_actual.html', 'w') as f:
        f.write(process_references(prepare_search_item_lists()))
    with open('./test_reference.html', 'r') as f:
        assert f.read() == process_references(prepare_search_item_lists()) + '\n'

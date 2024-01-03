from third_system.search_entity import SearchParam, SearchResponse
import requests


class UnifiedSearch:
    def __init__(self):
        self.base_url = "http://localhost:8000"

    def search(self, search_param: SearchParam) -> list[SearchResponse]:
        response = requests.post(self.base_url + "/search", json=search_param.dict())
        print(response.json())
        return [SearchResponse.parse_obj(item) for item in response.json()]


if __name__ == "__main__":
    UnifiedSearch().search(SearchParam(query="Hi TB Guru, please help me to cross check the standard pricing of ACH payment in Singapore and see if I can offer a unit rate of SGD 0.01 to the client."))

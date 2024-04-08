import os

import requests
from loguru import logger

from third_system.search_entity import SearchParam, KnowledgeSearchResponse

offline_token = f'''Bearer {os.environ.get("OFFLINE_TOKEN", "")}'''
knowledge_base_url = os.environ.get("KNOWLEDGE_BASE_URL",
                                    "https://bj.private.gluon-meson.tech:11000/components/knowledge-base")


class KnowledgeBase:
    def __init__(self):
        self.base_url = knowledge_base_url
        self.data_set_id_map = {
            "wealth_management": os.getenv("DATASET_ID_DICT_WEALTH_MANAGEMENT"),
        }

    def insurance_search(self, param: SearchParam, topic) -> KnowledgeSearchResponse:
        try:
            url = (f"{self.base_url}/components/knowledge-base/data-sets/{self.data_set_id_map[topic]}/search?size=10"
                   f"&page=1")
            payload = param.dict()
            query_response = requests.post(
                url=url,
                json=payload,
                headers={
                    "Authorization": offline_token
                }
            )
            if query_response.status_code is not 200:
                raise Exception(query_response.content)
            else:
                logger.debug(query_response.json())
        except Exception as e:
            logger.error(e)
        else:
            return KnowledgeSearchResponse.parse_obj(query_response.json())


if __name__ == "__main__":
    knowledge_base = KnowledgeBase()
    search_param = SearchParam(
        query="How to apply for insurance?",
        filters=[]
    )
    response = knowledge_base.insurance_search(search_param, topic="insurance_faq", )
    print(response)

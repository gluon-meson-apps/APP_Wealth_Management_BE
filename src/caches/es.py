import base64
import configparser
from typing import Union

import requests
from loguru import logger

from caches.base import Cache


class ElasticsearchCache(Cache):
    def __init__(self, list_flag=True, timeout=0.2):
        # 从config.ini文件中读取Elasticsearch连接参数
        config = configparser.ConfigParser()
        config.read("config.ini")
        credentials = f"{config.get('elasticsearch', 'username')}:{config.get('elasticsearch', 'password')}"
        token = base64.b64encode(credentials.encode("utf-8")).decode("utf-8")

        self.status = config.get("elasticsearch", "es_status")
        self.channel = config.get("elasticsearch", "es_channel")
        self.version = config.get("elasticsearch", "es_version_id")
        self.index = config.get("elasticsearch", "es_listed_index")
        self.host = config.get("elasticsearch", "host")
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Basic {token}",
        }

    def search(
        self,
        content: str,
        exact_match: bool = False,
        similarity_score_threshold: float = 0.02,
        limit=None,
    ) -> Union[str, None]:
        if not limit:
            limit = 20
        logger.info("ES search start")
        body = {
            "size": limit,
            "query": {
                "bool": {
                    "filter": [
                        {"term": {"version_id": {"value": self.version}}},
                        {"term": {"status": {"value": self.status}}},
                    ],
                    "must": [
                        {"match": {"content": content}},
                        {"match": {"channel.name": self.channel}},
                    ],
                }
            },
        }
        timeout_cnt = 0
        source_list = []
        for _ in range(3):
            try:
                url = self.host + "/" + self.index + "/_search"
                response = requests.post(url, headers=self.headers, json=body)
                source_list = response.json().get("hits").get("hits")
                break
            except Exception as e:
                timeout_cnt += 1
                if timeout_cnt >= 3:
                    logger.error("ES failed 3 times")
                    raise e
                else:
                    logger.error(f"ES failed {timeout_cnt} times")
                    logger.error(f"{str(e)}")
                    continue
        logger.info("ES search finished")

        def get_res(source_list):
            question_cands = []
            label_cands = []
            scores = []
            labelid_cands = []
            grammar_cands = []
            grammarid_cand = []
            if not source_list:
                return (
                    question_cands,
                    label_cands,
                    scores,
                    labelid_cands,
                    grammar_cands,
                    grammarid_cand,
                )
            for source in source_list:
                result = source["_source"]
                scores.append(source["_score"])
                question_cands.append(result["content"])
                label_cands.append(result["label"])
                labelid_cands.append(result["labelId"])
                grammar_cands.append(result["grammarConfig"])
                grammarid_cand.append(result["grammarConfigId"])
            return (
                question_cands,
                label_cands,
                scores,
                labelid_cands,
                grammar_cands,
                grammarid_cand,
            )

        return get_res(source_list)

import base64
import configparser

import requests
from elasticsearch import Elasticsearch
from loguru import logger


class ElasticsearchManager:
    def __init__(self, list_flag=True, timeout=0.2):
        # 从config.ini文件中读取Elasticsearch连接参数
        config = configparser.ConfigParser()
        config.read('config.ini')

        # 从配置文件中获取Elasticsearch连接参数
        es_config = {
            "host": config.get('elasticsearch', 'host'),
            "http_auth": (config.get('elasticsearch', 'username'),
                          config.get('elasticsearch', 'password')),
            "timeout": timeout,
            "max_retries": 1
        }

        # 初始化Elasticsearch连接
        self.es = Elasticsearch(
            hosts=es_config["host"],
            http_auth=es_config["http_auth"],
            timeout=es_config["timeout"],
            max_retries=es_config["max_retries"]
        )
        logger.info(f"ES info: {self.es.info}")
        self.status = config.get('elasticsearch', 'es_status')
        self.channel = config.get('elasticsearch', 'es_channel')
        self.index = config.get('elasticsearch', 'es_listed_index')
        self.alias = config.get('elasticsearch', 'es_listed_index')
        credentials = f"{config.get('elasticsearch', 'username')}:{config.get('elasticsearch', 'password')}"
        self.token = base64.b64encode(credentials.encode('utf-8')).decode('utf-8')
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Basic {self.token}"
        }
        self.host = config.get('elasticsearch', 'host')
        self.version = config.get('elasticsearch', 'es_version_id')

    def search_by_question(self, question, topk=20):
        body = {
            "size": topk,
            "query": {
                "bool": {
                    "filter": [
                        {"term": {"version_id": {"value": self.version}}},
                        {"term": {"status": {"value": self.status}}}
                    ],
                    "must": [
                        {"match": {"content": question}},
                        {"match": {"channel.name": self.channel}}
                    ]
                }
            }
        }
        timeout_cnt = 0
        source_list = []
        for _ in range(3):
            try:
                response = requests.post(self.host, headers=self.headers, json=body)
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
            for source in source_list:
                result = source["_source"]
                scores.append(source["_score"])
                question_cands.append(result["content"])
                label_cands.append(result["label"])
                labelid_cands.append(result["labelId"])
                grammar_cands.append(result["grammarConfig"])
                grammarid_cand.append(result["grammarConfigId"])
            return question_cands, label_cands, scores, labelid_cands, grammar_cands, grammarid_cand

        return get_res(source_list)

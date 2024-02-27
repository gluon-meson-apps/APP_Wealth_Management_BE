import configparser
import os
import json

from locust import HttpUser, task, between

from utils.common import get_config_path

config = configparser.ConfigParser()
config.read(get_config_path())

MODEL_URL = config['JointBert']['base_url']


class BertPerformanceTests(HttpUser):
    wait_time = between(1, 3)

    @task(1)
    def test_bert_predict(self):
        payload = {"input_text": "hi"}
        headers = {'Accept': 'application/json',
                   'Content-Type': 'application/json'}
        res = self.client.post(MODEL_URL,
                               data=json.dumps(payload),
                               headers=headers)
        print("res", res.json())

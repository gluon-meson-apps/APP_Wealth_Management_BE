import json
import time

from locust import HttpUser, task, between


class ApiPerformanceTests(HttpUser):
    wait_time = between(1, 3)

    def call_chat_api(self, user_input, session_id=""):
        second_payload = {"session_id": session_id, "user_input": user_input}
        headers = {'Accept': 'application/json',
                   'Content-Type': 'application/json'}
        res = self.client.post("/chat/",
                               data=json.dumps(second_payload),
                               headers=headers)
        return res.json()

    @task(1)
    def test_chat_api(self):
        res = self.call_chat_api("开通功能")
        print("res", res["response"] if res and "response" in res else "No valid response")

import requests


class UnifiedSearchClient:
    def __init__(self, base_url):
        self.base_url = base_url

    def send_request(self, method, path, params=None):
        if method == 'GET':
            return requests.get(self.base_url + path, params=params)
        if method == 'POST':
            return requests.post(self.base_url + path, data=params)

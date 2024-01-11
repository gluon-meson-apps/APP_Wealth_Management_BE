import os

import requests
from requests import Response

from third_system.search_entity import SearchItem


def mock_validate_res():
    mock_response = Response()
    mock_response.status_code = 200
    mock_response._content = """
    <body><div id="dummycontext"></div><div id="dummystatus"></div><div id="dummysummary"></div></body>
    """.encode()
    return mock_response


class HsbcConnectApi:
    def __init__(self):
        self.base_url = "https://hkl20146575.hc.cloud.hk.hsbc:25000/PaymentRulesValidator/Report"

    def validate_file(self, file: SearchItem) -> str:
        if file and file.text:
            # todo: currently mock response here
            response = (
                mock_validate_res()
                if os.getenv("LOCAL_MODE") == "1"
                else requests.post(self.base_url, files={"Attachment": file}, verify=False)
            )
            if response.status_code == 200:
                return response.text
        raise FileNotFoundError("No file valid.")

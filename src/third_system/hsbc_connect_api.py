import os

import requests

from third_system.search_entity import SearchItem


def mock_validate_res():
    file_dir = os.path.abspath(os.path.join(os.path.dirname(__file__)))
    with open(f"{file_dir}/file_validation_report.html", "r") as f:
        mock_response = requests.Response()
        mock_response.status_code = 200
        mock_response._content = f.read().encode("utf-8")
        return mock_response


class HsbcConnectApi:
    def __init__(self):
        self.base_url = os.getenv("HSBC_CONNECT_API_ENDPOINT")

    def validate_file(self, file: SearchItem) -> str:
        if file and file.text:
            response = (
                requests.post(self.base_url, files={"Attachment": file}, verify=False)
                if self.base_url
                else mock_validate_res()
            )
            if response.status_code == 200:
                return response.text
        raise FileNotFoundError("No file valid.")
